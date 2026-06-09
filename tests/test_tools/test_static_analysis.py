"""Tests for Static Analysis Agent and its parser."""
import pytest
from src.agents.static_analysis.agent import StaticAnalysisAgent
from src.agents.static_analysis.parser import (
    parse_semgrep_result, parse_linter_result, parse_ast_result,
    _infer_issue_type,
)
from src.tools.base import StructuredResult, ToolResult
from src.models.issue import IssueType


class TestParser:
    def test_parse_semgrep_result(self):
        result = StructuredResult(
            tool_name="semgrep",
            findings=[
                {
                    "rule_id": "python.security.sql-injection",
                    "path": "src/auth.py",
                    "start_line": 45,
                    "end_line": 45,
                    "message": "User input concatenated into SQL query",
                    "severity": "ERROR",
                    "category": "security",
                }
            ],
            summary="Found 1 issue",
            raw=ToolResult(tool_name="semgrep", exit_code=1),
        )
        issues = parse_semgrep_result(result)
        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.SECURITY
        assert issues[0].severity.value == "blocker"
        assert issues[0].confidence >= 0.9

    def test_parse_linter_result(self):
        result = StructuredResult(
            tool_name="pylint",
            findings=[
                {
                    "rule_id": "C0103",
                    "path": "test.py",
                    "line": 10,
                    "message": "Variable name doesn't conform to snake_case",
                    "type": "convention",
                }
            ],
            raw=ToolResult(tool_name="pylint", exit_code=0),
        )
        issues = parse_linter_result(result, "pylint")
        assert len(issues) == 1
        assert issues[0].severity.value == "info"

    def test_parse_ast_result_long_function(self):
        result = StructuredResult(
            tool_name="treesitter",
            findings=[{"type": "function_definition", "name": "big_func", "start_line": 1, "end_line": 60}],
            raw=ToolResult(tool_name="treesitter", exit_code=0),
        )
        issues = parse_ast_result(result, "test.py")
        assert len(issues) == 1
        assert "过长" in issues[0].title

    def test_parse_ast_result_short_function_ok(self):
        result = StructuredResult(
            tool_name="treesitter",
            findings=[{"type": "function_definition", "name": "small", "start_line": 1, "end_line": 10}],
            raw=ToolResult(tool_name="treesitter", exit_code=0),
        )
        issues = parse_ast_result(result, "test.py")
        assert len(issues) == 0

    def test_parse_empty_results(self):
        empty = StructuredResult(tool_name="semgrep", findings=[], raw=ToolResult(tool_name="semgrep", exit_code=0))
        assert parse_semgrep_result(empty) == []
        assert parse_linter_result(empty, "pylint") == []
        assert parse_ast_result(empty, "test.py") == []

    def test_infer_issue_type(self):
        assert _infer_issue_type("python-sql-injection") == IssueType.SECURITY
        assert _infer_issue_type("null-pointer-deref") == IssueType.BUG
        assert _infer_issue_type("complexity-too-high") == IssueType.MAINTAINABILITY
        assert _infer_issue_type("unknown-rule") == IssueType.MAINTAINABILITY


class TestStaticAnalysisAgent:
    @pytest.mark.asyncio
    async def test_creates_and_analyzes(self, sample_pr_info):
        agent = StaticAnalysisAgent()
        assert agent.agent_id == "static_analysis"

        result = await agent.analyze(sample_pr_info)
        assert result.status == "success"
        # May return 0 issues if tools not installed — graceful degradation
        assert isinstance(result.issues, list)

    @pytest.mark.asyncio
    async def test_empty_files_returns_empty(self):
        from src.models.pr import PRInfo
        agent = StaticAnalysisAgent()
        empty_pr = PRInfo(pr_id="empty", title="Empty", files_changed=[], files_count=0, additions=0, deletions=0)
        result = await agent.analyze(empty_pr)
        assert result.issues == []

    def test_capability(self):
        agent = StaticAnalysisAgent()
        cap = agent.get_capability()
        assert "security" in cap.change_types
        assert "python" in cap.languages
