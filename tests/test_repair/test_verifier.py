"""Tests for patch verification."""
import pytest
from src.agents.repair_patch.verifier import _check_syntax, _apply_patch
from src.models.patch import Patch


class TestApplyPatch:
    def test_no_change(self):
        result = _apply_patch("print(1)", "")
        assert result == "print(1)"

    def test_add_line(self):
        original = "def foo():\n    pass\n"
        diff = "--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,3 @@\n def foo():\n     pass\n+    return 1"
        result = _apply_patch(original, diff)
        assert "return 1" in result

    def test_remove_line(self):
        original = "x = 1\ny = 2\nz = 3\n"
        diff = "--- a/test.py\n+++ b/test.py\n@@ -1,3 +1,2 @@\n x = 1\n-y = 2\n z = 3"
        result = _apply_patch(original, diff)
        assert "y = 2" not in result


class TestCheckSyntax:
    def test_valid_code_passes(self):
        patch = Patch(
            patch_id="P1", issue_ids=[], unified_diff="",
            explanation="", files_modified=["test.py"],
        )
        assert _check_syntax(patch, "def foo():\n    return 1\n")

    def test_invalid_code_fails(self):
        patch = Patch(
            patch_id="P1", issue_ids=[], unified_diff="",
            explanation="", files_modified=["test.py"],
        )
        assert not _check_syntax(patch, "def foo(:\n    return 1\n")

    def test_patch_that_breaks_syntax(self):
        patch = Patch(
            patch_id="P1", issue_ids=[],
            unified_diff="--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-def foo():\n+def foo(:",
            explanation="", files_modified=["test.py"],
        )
        assert not _check_syntax(patch, "def foo():\n    pass\n")
