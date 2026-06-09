"""Tests for Semantic Review Agent."""
import pytest
from src.agents.semantic_review.agent import SemanticReviewAgent
from src.agents.semantic_review.context_builder import build_review_context


class TestContextBuilder:
    def test_builds_context(self, sample_pr_info):
        ctx = build_review_context(sample_pr_info, rag_results=[])
        assert len(ctx["code_snippets"]) == 1
        assert ctx["code_snippets"][0]["file_path"] == "src/auth.py"
        assert ctx["total_changed_files"] == 1

    def test_empty_rag_results(self, sample_pr_info):
        ctx = build_review_context(sample_pr_info, rag_results=[])
        assert ctx["conventions"] == []
        assert ctx["similar_bugs"] == []


class TestSemanticReviewAgent:
    @pytest.mark.asyncio
    async def test_creates_and_analyzes_mock(self, sample_pr_info):
        agent = SemanticReviewAgent(use_mock_llm=True)
        assert agent.agent_id == "semantic_review"

        result = await agent.analyze(sample_pr_info)
        assert result.status == "success"
        assert isinstance(result.issues, list)
        assert result.metadata.get("llm_mode") == "mock"

    @pytest.mark.asyncio
    async def test_empty_files_returns_fallback(self):
        from src.models.pr import PRInfo
        agent = SemanticReviewAgent(use_mock_llm=True)
        empty_pr = PRInfo(pr_id="empty", title="Empty", files_changed=[], files_count=0, additions=0, deletions=0)
        result = await agent.analyze(empty_pr)
        assert result.status == "success"

    def test_capability(self):
        agent = SemanticReviewAgent()
        cap = agent.get_capability()
        assert "security" in cap.change_types
        assert "architecture" in cap.change_types

    @pytest.mark.asyncio
    async def test_hardcoded_issues_fallback(self, sample_pr_info):
        agent = SemanticReviewAgent(use_mock_llm=True)
        issues = agent._hardcoded_issues(sample_pr_info)
        assert len(issues) == 1
        assert "LLM" in issues[0].title
