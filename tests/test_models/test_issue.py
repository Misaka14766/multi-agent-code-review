"""Tests for issue model validation and serialization."""
import json
import pytest
from src.models.issue import (
    Issue, IssueType, Severity, SourceLocation, Evidence, FixSuggestion, CodeReference,
)


class TestIssueModel:
    def test_issue_serialization(self, sample_issue: Issue):
        data = sample_issue.model_dump()
        assert data["issue_id"] == "TEST-001"
        assert data["severity"] == "blocker"
        assert data["confidence"] == 0.95
        assert data["location"]["file_path"] == "src/auth.py"

    def test_issue_deserialization(self, sample_issue: Issue):
        data = sample_issue.model_dump()
        restored = Issue(**data)
        assert restored.issue_id == sample_issue.issue_id
        assert restored.confidence == sample_issue.confidence

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            Issue(
                issue_id="X", issue_type=IssueType.BUG, severity=Severity.WARNING,
                title="", description="", location=SourceLocation(file_path="f", start_line=1, end_line=1),
                root_cause="", evidence=Evidence(code_snippet=""), confidence=1.5,
                source_agent="test",
            )

    def test_all_severity_values(self):
        for sev in Severity:
            issue = Issue(
                issue_id="X", issue_type=IssueType.BUG, severity=sev,
                title="", description="", location=SourceLocation(file_path="f", start_line=1, end_line=1),
                root_cause="", evidence=Evidence(code_snippet=""), confidence=0.5,
                source_agent="test",
            )
            assert issue.severity == sev

    def test_all_issue_types(self):
        for itype in IssueType:
            issue = Issue(
                issue_id="X", issue_type=itype, severity=Severity.INFO,
                title="", description="", location=SourceLocation(file_path="f", start_line=1, end_line=1),
                root_cause="", evidence=Evidence(code_snippet=""), confidence=0.5,
                source_agent="test",
            )
            assert issue.issue_type == itype

    def test_fix_suggestion_optional(self, sample_issue: Issue):
        issue = Issue(
            issue_id="X", issue_type=IssueType.BUG, severity=Severity.INFO,
            title="", description="", location=SourceLocation(file_path="f", start_line=1, end_line=1),
            root_cause="", evidence=Evidence(code_snippet=""), confidence=0.5,
            source_agent="test", fix_suggestion=None,
        )
        assert issue.fix_suggestion is None

    def test_evidence_with_references(self):
        evidence = Evidence(
            code_snippet="x = 1",
            ast_path="Module:body",
            similar_bug_refs=["Issue#1", "CVE-2023-XXXX"],
        )
        assert len(evidence.similar_bug_refs) == 2
        assert "Issue#1" in evidence.similar_bug_refs

    def test_json_roundtrip(self, sample_issue: Issue):
        json_str = json.dumps(sample_issue.model_dump(), ensure_ascii=False)
        data = json.loads(json_str)
        restored = Issue(**data)
        assert restored.issue_id == sample_issue.issue_id
        assert restored.confidence == sample_issue.confidence
