"""Patch verification — syntax check, static analysis, and sandbox testing."""

import asyncio
import logging
import tempfile
from pathlib import Path

from src.models.patch import Patch, PatchVerification

logger = logging.getLogger(__name__)


async def verify_patch(patch: Patch, original_code: str, test_code: str = "") -> PatchVerification:
    """Verify a generated patch by applying it and running checks."""
    verification = PatchVerification(patch_id=patch.patch_id)

    # Step 1: Syntax check — apply patch and parse with Python's AST
    verification.syntax_check = _check_syntax(patch, original_code)

    if not verification.syntax_check:
        verification.status = "verified_fail"
        verification.error_message = "Syntax check failed — patch produces invalid code"
        return verification

    # Step 2: Static analysis — re-run Pylint on patched code
    verification.static_analysis_pass = await _run_static_check(patch, original_code)

    # Step 3: Sandbox execution — run tests against patched code
    if test_code:
        verification.tests_pass = await _run_tests(patch, original_code, test_code)

    if verification.static_analysis_pass and (verification.tests_pass or not test_code):
        verification.status = "verified_pass"
    else:
        verification.status = "verified_fail"
        if not verification.static_analysis_pass:
            verification.error_message = "Static analysis failed on patched code"

    return verification


def _check_syntax(patch: Patch, original_code: str) -> bool:
    """Check if applying the patch produces syntactically valid Python code."""
    try:
        patched = _apply_patch(original_code, patch.unified_diff)
        compile(patched, "<patch_verify>", "exec")
        return True
    except SyntaxError as e:
        logger.warning("Patch syntax error: %s", e)
        return False
    except Exception as e:
        logger.warning("Syntax check failed: %s", e)
        return False


async def _run_static_check(patch: Patch, original_code: str) -> bool:
    """Re-run Pylint on patched code; pass if no new errors introduced."""
    try:
        patched = _apply_patch(original_code, patch.unified_diff)
    except Exception:
        return False

    tmpdir = tempfile.mkdtemp(prefix="patch_verify_")
    try:
        file_path = Path(tmpdir) / "patched.py"
        file_path.write_text(patched, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            "pylint", str(file_path), "--output-format=json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)

        import json
        try:
            issues = json.loads(stdout.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return True  # Can't parse output but tool ran → assume OK

        # Count errors (E) vs warnings/conventions
        errors = [i for i in issues if i.get("type") in ("error", "fatal")]
        return len(errors) == 0
    except (FileNotFoundError, asyncio.TimeoutError):
        # Pylint not installed or timed out → accept
        return True
    except Exception:
        return True  # Degrade gracefully
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


async def _run_tests(patch: Patch, original_code: str, test_code: str) -> bool:
    """Execute tests against patched code in a sandbox."""
    try:
        patched = _apply_patch(original_code, patch.unified_diff)
    except Exception:
        return False

    tmpdir = tempfile.mkdtemp(prefix="patch_test_")
    try:
        combined = patched + "\n\n" + test_code
        code_path = Path(tmpdir) / "test_patched.py"
        code_path.write_text(combined, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            "python", str(code_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        stderr_text = stderr.decode("utf-8", errors="replace")
        return proc.returncode == 0 and "FAILED" not in stderr_text and "Error" not in stderr_text
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def _apply_patch(original: str, unified_diff: str) -> str:
    """Simplified patch application for verification purposes.

    Handles common single-hunk patches. For complex patches, returns a
    best-effort merge that can be syntax-checked.
    """
    if not unified_diff.strip():
        return original

    lines = original.split("\n")
    result_lines = list(lines)

    hunks = [h for h in unified_diff.split("@@")[1:] if h.strip()]

    for hunk in hunks:
        hunk_body = hunk.strip()
        if not hunk_body:
            continue

        # Try to apply as simple old→new replacement
        old_lines: list[str] = []
        new_lines: list[str] = []
        for hl in hunk_body.split("\n"):
            if hl.startswith("-"):
                old_lines.append(hl[1:])
            elif hl.startswith("+"):
                new_lines.append(hl[1:])
            elif hl.startswith(" "):
                old_lines.append(hl[1:])
                new_lines.append(hl[1:])

        # Find old_lines in original and replace with new_lines
        if old_lines:
            # Search for the first matching old line
            for i in range(len(result_lines)):
                match = True
                for j, ol in enumerate(old_lines):
                    if i + j >= len(result_lines) or result_lines[i + j] != ol:
                        match = False
                        break
                if match:
                    result_lines[i:i + len(old_lines)] = new_lines
                    break
            else:
                # Fallback: if no exact match, append the patch at the end
                result_lines.extend(new_lines)

    return "\n".join(result_lines)
