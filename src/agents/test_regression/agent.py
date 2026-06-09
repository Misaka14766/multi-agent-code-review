"""Real Test & Regression Agent — coverage assessment + test generation."""

import time
import logging

from src.agents.base import BaseAgent, AgentConfig, AgentCapability, AgentResult
from src.models.pr import PRInfo
from src.models.issue import Issue, IssueType, Severity, SourceLocation, Evidence, FixSuggestion
from .coverage import analyze_coverage_for_changes
from .generator import generate_tests

logger = logging.getLogger(__name__)


class TestRegressionAgent(BaseAgent):
    """Evaluates test coverage and generates missing test cases.

    Pipeline:
      1. Analyze coverage for changed files
      2. Identify untested code paths
      3. Generate test stubs via LLM (mock or real)
    """

    def __init__(self, config: AgentConfig | None = None, use_mock: bool = True):
        cfg = config or AgentConfig(agent_id="test_regression", agent_name="Test & Regression Agent", timeout_seconds=45)
        super().__init__(cfg)
        self.use_mock = use_mock

    def get_capability(self) -> AgentCapability:
        return AgentCapability(
            change_types=["test", "logic", "security", "bug"],
            languages=["python", "javascript", "typescript"],
            produces=["issues", "tests"],
        )

    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        start = time.time()
        issues: list[Issue] = []

        files = pr_info.files_changed
        if not files:
            return AgentResult(agent_id=self.agent_id, status="success", issues=[], execution_time_ms=0)

        # Step 1: Coverage analysis for changed files
        changed_paths = [f.file_path for f in files]
        coverage_path = (context or {}).get("coverage_path")
        coverage = analyze_coverage_for_changes(coverage_path, changed_paths)

        if coverage.coverage_pct < 80 and coverage.total_lines > 0:
            issues.append(Issue(
                issue_id="TEST-COV-001",
                issue_type=IssueType.TEST_COVERAGE,
                severity=Severity.WARNING,
                title=f"测试覆盖率不足：{coverage.coverage_pct:.0f}%（阈值 80%）",
                description=f"变更文件覆盖率为 {coverage.coverage_pct:.1f}%，{len(coverage.gaps)} 行未覆盖。建议增加测试用例。",
                location=SourceLocation(file_path=changed_paths[0] if changed_paths else "", start_line=1, end_line=1),
                root_cause="代码变更未伴随足够的测试用例更新",
                evidence=Evidence(code_snippet=f"Coverage: {coverage.coverage_pct:.1f}%, Uncovered: {len(coverage.gaps)} lines"),
                confidence=0.85,
                source_agent=self.agent_id,
            ))

        # Step 2: Generate test cases
        code_to_test = "\n".join(
            f.new_content or "" for f in files if f.new_content
        )[:5000]

        if code_to_test.strip():
            gen_issues = (context or {}).get("target_issues", [])
            issue_dicts = [{"id": i.issue_id, "title": i.title, "description": i.description} for i in gen_issues]

            try:
                test_cases = await generate_tests(code_to_test, issue_dicts, use_mock=self.use_mock)
            except Exception as e:
                logger.warning("Test generation failed: %s", e)
                test_cases = []

            # Report each generated test as an issue (suggestion to add it)
            for tc in test_cases:
                issues.append(Issue(
                    issue_id=f"TEST-GEN-{test_cases.index(tc)+1:03d}",
                    issue_type=IssueType.TEST_COVERAGE,
                    severity=Severity.SUGGESTION,
                    title=f"建议添加测试：{tc.get('test_name', 'untitled')}",
                    description=tc.get("description", "Auto-generated test suggestion"),
                    location=SourceLocation(
                        file_path=changed_paths[0] if changed_paths else "",
                        start_line=1, end_line=1,
                    ),
                    root_cause="自动分析发现缺少边界条件/安全测试覆盖",
                    evidence=Evidence(code_snippet=tc.get("test_code", "")[:500]),
                    fix_suggestion=FixSuggestion(
                        unified_diff=f"+{tc.get('test_code', '')}",
                        explanation=f"添加测试用例: {tc.get('test_name', '')}",
                    ) if tc.get("test_code") else None,
                    confidence=0.75,
                    source_agent=self.agent_id,
                ))

        elapsed = (time.time() - start) * 1000

        # If no coverage data and no code to test, provide a generic suggestion
        if not issues and files:
            issues.append(Issue(
                issue_id="TEST-INFO-001",
                issue_type=IssueType.TEST_COVERAGE,
                severity=Severity.INFO,
                title="建议确认变更代码有对应的测试覆盖",
                description=f"变更了 {len(files)} 个文件，请确认已有测试覆盖关键路径。",
                location=SourceLocation(file_path=changed_paths[0], start_line=1, end_line=1),
                root_cause="无覆盖率报告可用，无法自动评估",
                evidence=Evidence(code_snippet=""),
                confidence=0.5,
                source_agent=self.agent_id,
            ))

        return AgentResult(
            agent_id=self.agent_id,
            status="success",
            issues=issues,
            execution_time_ms=elapsed,
            metadata={
                "coverage_pct": coverage.coverage_pct,
                "tests_generated": len([i for i in issues if i.issue_id.startswith("TEST-GEN")]),
                "llm_mode": "mock" if self.use_mock else "deepseek",
            },
        )
