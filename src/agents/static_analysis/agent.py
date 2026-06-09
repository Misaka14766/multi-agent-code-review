"""Real Static Analysis Agent — orchestrates Semgrep + Pylint + Tree-sitter."""

import asyncio
import os
import tempfile
import time
from pathlib import Path

from src.agents.base import BaseAgent, AgentConfig, AgentCapability, AgentResult
from src.models.pr import PRInfo
from src.models.issue import Issue
from src.tools.semgrep_tool import SemgrepTool
from src.tools.linter_tool import LinterTool
from src.tools.treesitter_tool import TreeSitterTool
from .parser import parse_semgrep_result, parse_linter_result, parse_ast_result
from .runner import run_all_tools


class StaticAnalysisAgent(BaseAgent):
    """Runs static analysis tools (Semgrep, Pylint, Tree-sitter) on code changes."""

    def __init__(self, config: AgentConfig | None = None):
        cfg = config or AgentConfig(agent_id="static_analysis", agent_name="Static Analysis Agent")
        super().__init__(cfg)
        self._semgrep = SemgrepTool()
        self._linter = LinterTool("pylint")
        self._treesitter = TreeSitterTool()

    def get_capability(self) -> AgentCapability:
        return AgentCapability(
            change_types=["security", "style", "maintainability", "bug"],
            languages=["python", "javascript", "typescript"],
            produces=["issues"],
        )

    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        start = time.time()
        all_issues: list[Issue] = []

        files = pr_info.files_changed
        if not files:
            return AgentResult(agent_id=self.agent_id, status="success", issues=[], execution_time_ms=0)

        # Write changed files to a temp dir so tools can scan them
        tmpdir = tempfile.mkdtemp(prefix="sa_review_")
        try:
            for f in files:
                if f.new_content:
                    dest = Path(tmpdir) / os.path.basename(f.file_path)
                    dest.write_text(f.new_content, encoding="utf-8")

            # Run Semgrep + Pylint + Tree-sitter in parallel
            results = await run_all_tools(
                [self._semgrep, self._linter, self._treesitter],
                {"target_dir": tmpdir, "target_file": str(Path(tmpdir) / os.path.basename(files[0].file_path)) if files else ".", "languages": ["python"]},
            )

            for result in results:
                if result.tool_name == "semgrep" and result.findings:
                    all_issues.extend(parse_semgrep_result(result))
                elif result.tool_name in ("pylint", "eslint") and result.findings:
                    all_issues.extend(parse_linter_result(result, result.tool_name))
                elif result.tool_name == "treesitter" and result.findings:
                    all_issues.extend(parse_ast_result(result, files[0].file_path if files else ""))

        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

        # Deduplicate by (file, line)
        seen: set[tuple[str, int]] = set()
        deduped: list[Issue] = []
        for issue in all_issues:
            key = (issue.location.file_path, issue.location.start_line)
            if key not in seen:
                seen.add(key)
                deduped.append(issue)

        elapsed = (time.time() - start) * 1000

        # If no tools found anything, fall back to empty (tools may not be installed)
        return AgentResult(
            agent_id=self.agent_id,
            status="success",
            issues=deduped,
            execution_time_ms=elapsed,
            metadata={"tools_used": len([r for r in results if r.raw and r.raw.exit_code >= 0]) if results else 0},
        )
