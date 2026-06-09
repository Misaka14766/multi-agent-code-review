"""Tests for Agent base class and registry."""
import pytest
from src.agents.base import BaseAgent, AgentConfig, AgentCapability, AgentResult, AgentRegistry, agent_registry


class TestAgentRegistry:
    def test_registry_singleton(self):
        r1 = AgentRegistry()
        r2 = AgentRegistry()
        # Module-level singleton is separate from new instances
        assert agent_registry is not None

    def test_register_and_get(self, registered_agents):
        agent = registered_agents.get("static_analysis")
        assert agent is not None
        assert agent.agent_id == "static_analysis"

    def test_list_all(self, registered_agents):
        agents = registered_agents.list_all()
        assert len(agents) == 4

    def test_get_nonexistent(self, registered_agents):
        assert registered_agents.get("nonexistent") is None

    def test_get_by_capability(self, registered_agents):
        agents = registered_agents.get_by_capability("security")
        agent_ids = [a.agent_id for a in agents]
        assert "static_analysis" in agent_ids
        assert "semantic_review" in agent_ids

    def test_health_check_all(self, registered_agents):
        import asyncio
        results = asyncio.run(registered_agents.health_check_all())
        assert len(results) == 4
        assert all(results.values())


class TestAgentConfig:
    def test_default_config(self):
        cfg = AgentConfig(agent_id="test", agent_name="Test Agent")
        assert cfg.enabled is True
        assert cfg.timeout_seconds == 30


class TestAgentCapability:
    def test_capability_matching(self):
        cap = AgentCapability(
            change_types=["security", "bug"],
            languages=["python"],
            produces=["issues"],
        )
        assert "security" in cap.change_types
        assert "python" in cap.languages


class TestAgentResult:
    def test_success_result(self):
        result = AgentResult(agent_id="test", status="success")
        assert result.status == "success"
        assert len(result.issues) == 0
