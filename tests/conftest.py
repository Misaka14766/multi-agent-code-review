"""Shared fixtures for the test suite."""
import pytest
from src.models.pr import PRInfo, FileDiff
from src.models.issue import Issue, IssueType, Severity, SourceLocation, Evidence, FixSuggestion
from src.agents.mock_agents import register_mock_agents
from src.orchestrator.graph import ReviewOrchestrator

SAMPLE_CODE = 'def login(u, p):\n    query = f"SELECT * FROM users WHERE name = {u}"\n    cursor.execute(query)\n'


@pytest.fixture
def sample_file_diff() -> FileDiff:
    return FileDiff(
        file_path="src/auth.py",
        change_type="modified",
        new_content=SAMPLE_CODE,
        language="python",
    )


@pytest.fixture
def sample_pr_info(sample_file_diff: FileDiff) -> PRInfo:
    return PRInfo(
        pr_id="test-001",
        title="Test PR: Fix auth",
        description="Test PR for unit tests",
        repo_url="https://github.com/test/repo",
        base_branch="main",
        head_branch="fix/auth",
        author="test-user",
        files_changed=[sample_file_diff],
        files_count=1,
        additions=3,
        deletions=0,
    )


@pytest.fixture
def sample_issue() -> Issue:
    return Issue(
        issue_id="TEST-001",
        issue_type=IssueType.SECURITY,
        severity=Severity.BLOCKER,
        title="SQL Injection in login",
        description="User input concatenated into SQL query",
        location=SourceLocation(file_path="src/auth.py", start_line=2, end_line=2),
        root_cause="String interpolation instead of parameterized query",
        evidence=Evidence(code_snippet='query = f"SELECT * FROM users WHERE name = {u}"'),
        fix_suggestion=FixSuggestion(
            unified_diff="-old\n+new",
            explanation="Use parameterized queries",
        ),
        confidence=0.95,
        source_agent="static_analysis",
    )


@pytest.fixture
def registered_agents():
    """Register all mock agents and clean up after test."""
    registry = register_mock_agents()
    yield registry
    registry._agents.clear()


@pytest.fixture
def orchestrator(registered_agents):
    """Create an orchestrator with mock agents registered."""
    return ReviewOrchestrator()
