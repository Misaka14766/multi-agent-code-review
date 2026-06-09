"""Tests for individual orchestrator node functions."""
from src.orchestrator.state import (
    ReviewState, ChangeClassification, QualityGateDecision, AgentAssignment,
)
from src.orchestrator.nodes.ingestion import ingest_pr
from src.orchestrator.nodes.classification import classify_changes
from src.orchestrator.nodes.arbitration import arbitrate
from src.orchestrator.nodes.quality_gate import quality_gate


def _make_state(**overrides) -> ReviewState:
    s: ReviewState = {
        "review_id": "test",
        "pr_info": None,  # type: ignore[typeddict-item]
        "code_changes": [],
        "change_classification": ChangeClassification(),
        "agent_assignments": [],
        "static_analysis_issues": [],
        "semantic_review_issues": [],
        "test_regression_issues": [],
        "consolidated_issues": [],
        "conflicts": [],
        "quality_gate_decision": None,  # type: ignore[typeddict-item]
        "repair_attempt": 0,
        "current_repair_result": None,  # type: ignore[typeddict-item]
        "repair_history": [],
        "agent_reports": [],
        "final_report": {},
        "review_status": "pending",
        "errors": [],
        "agent_status": {},
        "agent_timing": {},
    }
    s.update(overrides)  # type: ignore[typeddict-item]
    return s


class TestIngestion:
    def test_ingest_updates_code_changes(self, sample_pr_info):
        state = _make_state(pr_info=sample_pr_info)
        result = ingest_pr(state)
        assert result["code_changes"] is not None
        assert len(result["code_changes"]) == 1
        assert result["review_status"] == "in_progress"

    def test_ingest_no_files_adds_error(self):
        from src.models.pr import PRInfo
        empty_pr = PRInfo(pr_id="empty", title="Empty", files_changed=[], files_count=0, additions=0, deletions=0)
        state = _make_state(pr_info=empty_pr)
        result = ingest_pr(state)
        assert "No files to review" in result.get("errors", [])


class TestClassification:
    def test_classify_security_change(self, sample_pr_info):
        state = _make_state(pr_info=sample_pr_info, code_changes=sample_pr_info.files_changed)
        result = classify_changes(state)
        cc = result["change_classification"]
        assert cc is not None
        assert len(result["agent_assignments"]) > 0

    def test_classify_empty_files(self):
        state = _make_state(code_changes=[])
        result = classify_changes(state)
        assert result["agent_assignments"] == []


class TestArbitration:
    def test_arbitrate_empty_issues(self):
        state = _make_state()
        result = arbitrate(state)
        assert result["consolidated_issues"] == []
        assert result["conflicts"] == []

    def test_arbitrate_dedup_by_location(self, sample_issue):
        from src.models.issue import Issue, IssueType, Severity, SourceLocation, Evidence
        issue_b = Issue(
            issue_id="B-001",
            issue_type=IssueType.BUG, severity=Severity.WARNING,
            title="Duplicate location", description="",
            location=SourceLocation(file_path="src/auth.py", start_line=2, end_line=2),
            root_cause="", evidence=Evidence(code_snippet="x"), confidence=0.5,
            source_agent="semantic_review",
        )
        state = _make_state(
            static_analysis_issues=[sample_issue],
            semantic_review_issues=[issue_b],
        )
        result = arbitrate(state)
        # Higher confidence issue should win at the same location
        assert len(result["consolidated_issues"]) == 1
        assert result["consolidated_issues"][0].issue_id == "TEST-001"


class TestQualityGate:
    def test_empty_issues_pass(self):
        state = _make_state()
        result = quality_gate(state)
        assert result["quality_gate_decision"].verdict == "pass"

    def test_blocker_issues(self, sample_issue):
        state = _make_state(consolidated_issues=[sample_issue])
        result = quality_gate(state)
        assert result["quality_gate_decision"].verdict == "blocked"
        assert result["quality_gate_decision"].blocker_count == 1

    def test_security_requires_human(self, sample_issue):
        state = _make_state(consolidated_issues=[sample_issue])
        result = quality_gate(state)
        assert result["quality_gate_decision"].requires_human is True
