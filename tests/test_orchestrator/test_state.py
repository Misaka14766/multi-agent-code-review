"""Tests for orchestrator state definitions."""
from src.orchestrator.state import (
    ReviewState, ChangeClassification, AgentAssignment,
    Conflict, RepairResult,
)


class TestChangeClassification:
    def test_defaults(self):
        cc = ChangeClassification()
        assert cc.primary_type == "logic"
        assert cc.risk_score == 0.5
        assert cc.recommended_agents == []

    def test_custom(self):
        cc = ChangeClassification(
            primary_type="security",
            secondary_types=["logic"],
            affected_modules=["auth"],
            risk_score=0.9,
            recommended_agents=["static_analysis", "semantic_review"],
        )
        assert cc.primary_type == "security"
        assert cc.risk_score == 0.9
        assert len(cc.recommended_agents) == 2

    def test_risk_score_bounds(self):
        import pytest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChangeClassification(risk_score=1.5)
        with pytest.raises(ValidationError):
            ChangeClassification(risk_score=-0.1)


class TestAgentAssignment:
    def test_basic(self):
        aa = AgentAssignment(agent_id="static_analysis", reason="Security check", priority=1)
        assert aa.agent_id == "static_analysis"
        assert aa.priority == 1


class TestConflict:
    def test_basic(self):
        c = Conflict(
            conflict_id="CONF-001",
            issue_a_id="SA-001",
            issue_b_id="SEM-001",
            description="Disagreement on severity",
        )
        assert c.resolution == ""
        assert c.resolved_by == ""


class TestRepairResult:
    def test_default(self):
        rr = RepairResult()
        assert rr.success is False
        assert rr.patch is None
        assert rr.verification is None

    def test_success(self):
        rr = RepairResult(success=True)
        assert rr.success is True
