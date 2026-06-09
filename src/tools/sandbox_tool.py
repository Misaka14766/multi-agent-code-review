"""Sandbox tool — isolated execution for test and patch verification."""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from .base import ToolInterface, ToolPlan, ToolResult, StructuredResult


class SandboxTool(ToolInterface):
    """Executes code in an isolated temporary directory for safe verification."""

    def __init__(self):
        super().__init__("sandbox")

    async def plan(self, context: dict) -> ToolPlan:
        return ToolPlan(
            tool_name="sandbox",
            parameters={
                "code": context.get("code", ""),
                "test_code": context.get("test_code", ""),
                "timeout": context.get("timeout", 30),
            },
            reason="Isolated code execution for verification",
            timeout_seconds=context.get("timeout", 30) + 10,
        )

    async def execute(self, plan: ToolPlan) -> ToolResult:
        start = time.time()
        code = plan.parameters.get("code", "")
        test_code = plan.parameters.get("test_code", "")
        exec_timeout = plan.parameters.get("timeout", 30)

        if not code and not test_code:
            return ToolResult(tool_name="sandbox", exit_code=-1, stderr="No code to execute")

        tmpdir = tempfile.mkdtemp(prefix="code_review_")
        try:
            # Write code to temp file
            code_path = Path(tmpdir) / "code_under_test.py"
            combined = code + "\n\n" + test_code if test_code else code
            code_path.write_text(combined, encoding="utf-8")

            proc = await asyncio.create_subprocess_exec(
                "python", str(code_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=exec_timeout)
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                tool_name="sandbox",
                exit_code=proc.returncode or 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                execution_time_ms=elapsed,
            )
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            return ToolResult(tool_name="sandbox", exit_code=-2, stderr="Execution timed out", execution_time_ms=elapsed)
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ToolResult(tool_name="sandbox", exit_code=-1, stderr=str(e), execution_time_ms=elapsed)
        finally:
            # Cleanup temp dir
            try:
                import shutil
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    def parse(self, raw: ToolResult) -> StructuredResult:
        success = raw.exit_code == 0
        findings = []
        if not success:
            findings.append({
                "type": "execution_error",
                "exit_code": raw.exit_code,
                "stdout": raw.stdout,
                "stderr": raw.stderr,
                "summary": "Code execution failed" if raw.exit_code > 0 else "Timeout or setup error",
            })
        return StructuredResult(
            tool_name="sandbox",
            findings=findings,
            summary=f"Execution {'passed' if success else 'failed'} (exit code {raw.exit_code})",
            raw=raw,
        )

    async def validate(self, result: StructuredResult) -> bool:
        return result.raw is not None
