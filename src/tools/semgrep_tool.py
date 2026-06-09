"""Semgrep tool — static pattern matching for security and style issues."""

import asyncio
import json
import os
import time
from .base import ToolInterface, ToolPlan, ToolResult, StructuredResult


class SemgrepTool(ToolInterface):
    """Wraps Semgrep CLI for pattern-based code analysis."""

    def __init__(self, config: str = "auto"):
        super().__init__("semgrep")
        self.config = config

    async def plan(self, context: dict) -> ToolPlan:
        target_dir = context.get("target_dir", ".")
        languages = context.get("languages", ["python"])
        return ToolPlan(
            tool_name="semgrep",
            parameters={
                "target": target_dir,
                "lang": languages,
                "config": self.config,
            },
            reason=f"Static pattern matching for {languages}",
            timeout_seconds=120,
        )

    async def execute(self, plan: ToolPlan) -> ToolResult:
        start = time.time()
        cmd = [
            "semgrep", "scan",
            "--config", plan.parameters.get("config", "auto"),
            "--json",
            "--quiet",
        ]

        target = plan.parameters.get("target", ".")
        cmd.append(target)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=plan.timeout_seconds
            )
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                tool_name="semgrep",
                exit_code=proc.returncode or 0,
                stdout=stdout.decode("utf-8", errors="ignore"),
                stderr=stderr.decode("utf-8", errors="ignore"),
                execution_time_ms=elapsed,
            )
        except FileNotFoundError:
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                tool_name="semgrep",
                exit_code=-1,
                stderr="Semgrep not installed. Install with: pip install semgrep",
                execution_time_ms=elapsed,
            )
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                tool_name="semgrep",
                exit_code=-2,
                stderr="Semgrep timed out",
                execution_time_ms=elapsed,
            )

    def parse(self, raw: ToolResult) -> StructuredResult:
        if raw.exit_code < 0:
            return StructuredResult(
                tool_name="semgrep",
                findings=[],
                summary=f"Semgrep unavailable: {raw.stderr}",
                raw=raw,
            )
        try:
            data = json.loads(raw.stdout)
        except json.JSONDecodeError:
            return StructuredResult(tool_name="semgrep", findings=[], summary="Failed to parse Semgrep output", raw=raw)
        results = data.get("results", [])
        findings = []
        for r in results:
            findings.append({
                "rule_id": r.get("check_id", ""),
                "path": r.get("path", ""),
                "start_line": r.get("start", {}).get("line", 0),
                "end_line": r.get("end", {}).get("line", 0),
                "message": r.get("extra", {}).get("message", ""),
                "severity": r.get("extra", {}).get("severity", "WARNING"),
                "category": r.get("extra", {}).get("metadata", {}).get("category", ""),
            })
        return StructuredResult(
            tool_name="semgrep",
            findings=findings,
            summary=f"Found {len(findings)} issue(s)",
            raw=raw,
        )

    async def validate(self, result: StructuredResult) -> bool:
        return result.raw is not None and result.raw.exit_code in (0, 1, -1)
