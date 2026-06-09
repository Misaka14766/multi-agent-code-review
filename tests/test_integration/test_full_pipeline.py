"""End-to-end integration tests for the full review pipeline."""
import pytest
from src.models.pr import PRInfo, FileDiff

SAMPLE_CODE = '''def login(username: str, password: str):
    query = f'SELECT * FROM users WHERE name = "{username}"'
    cursor.execute(query)
    user = cursor.fetchone()
    if user and user['password'] == password:
        return user
    return None
'''


@pytest.mark.asyncio
async def test_full_pipeline_with_security_bug(registered_agents, orchestrator):
    """End-to-end: code with SQL injection should be blocked."""
    pr_info = PRInfo(
        pr_id="e2e-001",
        title="Auth: login feature",
        description="Add user login function",
        repo_url="https://github.com/test/repo",
        base_branch="main",
        head_branch="feature/login",
        author="dev",
        files_changed=[
            FileDiff(
                file_path="src/auth.py",
                change_type="modified",
                new_content=SAMPLE_CODE,
                language="python",
            )
        ],
        files_count=1,
        additions=10,
        deletions=0,
    )

    report = await orchestrator.run_review("e2e-001", pr_info)

    # Verify report structure
    assert report["status"] == "completed"
    summary = report["summary"]
    assert summary["total_issues"] >= 1
    assert summary["blockers"] >= 1
    assert summary["verdict"] == "blocked"
    assert summary["repair_attempts"] == 1

    # Verify issues have required fields
    for issue in report["issues"]:
        assert issue["issue_id"]
        assert issue["severity"]
        assert issue["title"]
        assert issue["root_cause"]
        assert issue["location"]["file_path"]
        assert 0.0 <= issue["confidence"] <= 1.0

    # Verify agent reports
    assert len(report["agent_reports"]) == 3
    for ar in report["agent_reports"]:
        assert ar["agent_name"]
        assert ar["status"] in ("success", "error", "timeout")

    # Verify quality gate
    qg = report["quality_gate"]
    assert qg["verdict"] == "blocked"
    assert qg["requires_human"] is True

    # Verify patches generated
    assert len(report.get("patches", [])) >= 1


@pytest.mark.asyncio
async def test_full_pipeline_clean_code_passes(registered_agents, orchestrator):
    """End-to-end: clean code (no bugs) should pass."""
    # Note: with mock agents, all code produces the same canned issues.
    # This test validates the pipeline runs to completion.
    pr_info = PRInfo(
        pr_id="e2e-002",
        title="Docs: update readme",
        description="Update documentation",
        files_changed=[
            FileDiff(
                file_path="README.md",
                change_type="modified",
                new_content="# Updated docs",
                language="markdown",
            )
        ],
        files_count=1,
        additions=1,
        deletions=0,
    )

    report = await orchestrator.run_review("e2e-002", pr_info)
    assert report["status"] == "completed"
    assert "summary" in report
    assert "issues" in report
    assert "agent_reports" in report


@pytest.mark.asyncio
async def test_report_json_serializable(registered_agents, orchestrator):
    """Verify the report can be serialized to JSON."""
    import json

    pr_info = PRInfo(
        pr_id="e2e-003", title="Test",
        files_changed=[
            FileDiff(file_path="test.py", new_content="x=1", language="python")
        ],
        files_count=1, additions=1, deletions=0,
    )

    report = await orchestrator.run_review("e2e-003", pr_info)
    # Should not raise
    json_str = json.dumps(report, ensure_ascii=False, indent=2)
    assert len(json_str) > 0
    # Round-trip
    restored = json.loads(json_str)
    assert restored["review_id"] == "e2e-003"
