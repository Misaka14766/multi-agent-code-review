"""Tests for tool abstraction layer."""
import pytest
from src.tools.base import ToolPlan, ToolResult, StructuredResult, ToolInterface


class TestToolPlan:
    def test_default_plan(self):
        plan = ToolPlan(tool_name="test")
        assert plan.tool_name == "test"
        assert plan.timeout_seconds == 60

    def test_custom_plan(self):
        plan = ToolPlan(tool_name="semgrep", parameters={"target": "."}, reason="test", timeout_seconds=30)
        assert plan.parameters["target"] == "."
        assert plan.reason == "test"


class TestToolResult:
    def test_success_result(self):
        result = ToolResult(tool_name="test", exit_code=0, stdout='{"ok": true}')
        assert result.exit_code == 0

    def test_error_result(self):
        result = ToolResult(tool_name="test", exit_code=1, stderr="Error message")
        assert result.exit_code == 1
        assert "Error" in result.stderr


class TestStructuredResult:
    def test_with_findings(self):
        sr = StructuredResult(
            tool_name="semgrep",
            findings=[{"rule_id": "test-rule", "path": "test.py", "line": 10}],
            summary="Found 1 issue",
        )
        assert len(sr.findings) == 1
        assert sr.summary == "Found 1 issue"

    def test_empty(self):
        sr = StructuredResult(tool_name="pylint")
        assert sr.findings == []
        assert sr.raw is None


class TestToolRegistry:
    def test_register_and_get(self):
        from src.tools.registry import ToolRegistry
        from src.tools.semgrep_tool import SemgrepTool

        registry = ToolRegistry()
        tool = SemgrepTool()
        registry.register(tool)
        assert registry.get("semgrep") is not None
        assert "semgrep" in registry.list_names()
        assert registry.is_available("semgrep")
        assert not registry.is_available("nonexistent")
