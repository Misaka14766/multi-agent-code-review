"""Tests for mock agent implementations."""
import asyncio
import pytest
from src.agents.mock_agents import (
    MockStaticAnalysisAgent, MockSemanticReviewAgent,
    MockTestRegressionAgent, MockRepairPatchAgent,
)
from src.models.issue import Issue


class TestMockStaticAnalysisAgent:
    @pytest.mark.asyncio
    async def test_analyze_returns_issues(self, sample_pr_info):
        agent = MockStaticAnalysisAgent()
        result = await agent.analyze(sample_pr_info)
        assert result.status == "success"
        assert len(result.issues) == 3
        for issue in result.issues:
            assert isinstance(issue, Issue)
        assert any(i.severity.value == "blocker" for i in result.issues)

    def test_capability(self):
        agent = MockStaticAnalysisAgent()
        cap = agent.get_capability()
        assert "security" in cap.change_types
        assert "python" in cap.languages


class TestMockSemanticReviewAgent:
    @pytest.mark.asyncio
    async def test_analyze_returns_issues(self, sample_pr_info):
        agent = MockSemanticReviewAgent()
        result = await agent.analyze(sample_pr_info)
        assert result.status == "success"
        assert len(result.issues) == 3
        assert any("SQL" in i.title for i in result.issues)

    def test_can_handle(self):
        agent = MockSemanticReviewAgent()
        assert agent.can_handle("security")
        assert agent.can_handle("architecture")
        assert not agent.can_handle("docs")


class TestMockTestRegressionAgent:
    @pytest.mark.asyncio
    async def test_analyze_returns_issues(self, sample_pr_info):
        agent = MockTestRegressionAgent()
        result = await agent.analyze(sample_pr_info)
        assert result.status == "success"
        assert len(result.issues) == 2
        assert all(i.issue_type.value == "test_coverage" for i in result.issues)

    def test_metadata(self):
        agent = MockTestRegressionAgent()
        # Metadata is returned in analyze
        assert agent.get_capability().produces == ["issues", "tests"]


class TestMockRepairPatchAgent:
    @pytest.mark.asyncio
    async def test_analyze_with_context(self, sample_pr_info):
        agent = MockRepairPatchAgent()
        result = await agent.analyze(sample_pr_info, {"target_issues": []})
        assert result.status == "success"
        patches = result.metadata.get("patches", [])
        assert len(patches) == 1
        assert patches[0]["patch_id"] == "PATCH-001"
        assert "unified_diff" in patches[0]
