"""Linter tool — unified interface for Pylint and ESLint."""

import asyncio
import json
import time
from .base import ToolInterface, ToolPlan, ToolResult, StructuredResult


class LinterTool(ToolInterface):
    """Wraps Pylint (Python) or ESLint (JavaScript) for style/quality checks."""

    def __init__(self, linter: str = "pylint"):
        super().__init__(linter)
        self.linter = linter

    async def plan(self, context: dict) -> ToolPlan:
        target = context.get("target_file", context.get("target_dir", "."))
        return ToolPlan(
            tool_name=self.linter,
            parameters={"target": target},
            reason=f"Style and quality check with {self.linter}",
            timeout_seconds=60,
        )

    async def execute(self, plan: ToolPlan) -> ToolResult:
        start = time.time()
        target = plan.parameters.get("target", ".")

        if self.linter == "pylint":
            cmd = ["pylint", "--output-format=json", target]
        elif self.linter == "eslint":
            cmd = ["eslint", "--format=json", target]
        else:
            return ToolResult(tool_name=self.linter, exit_code=-1, stderr=f"Unknown linter: {self.linter}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=plan.timeout_seconds)
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                tool_name=self.linter,
                exit_code=proc.returncode or 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                execution_time_ms=elapsed,
            )
        except FileNotFoundError:
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                tool_name=self.linter,
                exit_code=-1,
                stderr=f"{self.linter} not installed",
                execution_time_ms=elapsed,
            )
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            return ToolResult(tool_name=self.linter, exit_code=-2, stderr="Linter timed out", execution_time_ms=elapsed)

    def parse(self, raw: ToolResult) -> StructuredResult:
        if raw.exit_code < 0:
            return StructuredResult(tool_name=self.linter, findings=[], summary=f"Linter unavailable: {raw.stderr}", raw=raw)
        try:
            data = json.loads(raw.stdout)
        except json.JSONDecodeError:
            return StructuredResult(tool_name=self.linter, findings=[], summary="Failed to parse linter output", raw=raw)

        findings = []
        if self.linter == "pylint":
            for entry in data if isinstance(data, list) else []:
                findings.append({
                    "rule_id": entry.get("message-id", entry.get("symbol", "")),
                    "path": entry.get("path", ""),
                    "line": entry.get("line", 0),
                    "message": entry.get("message", ""),
                    "type": entry.get("type", ""),
                })
        elif self.linter == "eslint":
            for file_entry in data if isinstance(data, list) else []:
                for msg in file_entry.get("messages", []):
                    findings.append({
                        "rule_id": msg.get("ruleId", ""),
                        "path": file_entry.get("filePath", ""),
                        "line": msg.get("line", 0),
                        "message": msg.get("message", ""),
                        "severity": "error" if msg.get("severity", 0) >= 2 else "warning",
                    })
        return StructuredResult(
            tool_name=self.linter,
            findings=findings,
            summary=f"Found {len(findings)} issue(s)",
            raw=raw,
        )

    async def validate(self, result: StructuredResult) -> bool:
        # Pylint returns 0-32 for various states; all are valid (parsed successfully)
        return result.raw is not None and result.raw.exit_code >= -1
