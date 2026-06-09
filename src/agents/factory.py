"""Agent factory — switches between mock and real agents based on LLM_PROVIDER."""

from .base import agent_registry, AgentConfig
from config.settings import settings


_PLACEHOLDER_KEYS = {"sk-你的密钥", "sk-your-key", "sk-your-api-key", "sk-xxx", ""}


def register_agents(force_mock: bool = False) -> None:
    """Register agents. Uses real agents if LLM_PROVIDER=deepseek and a valid API key is set."""
    api_key = settings.DEEPSEEK_API_KEY.strip()
    is_placeholder = api_key.lower() in _PLACEHOLDER_KEYS or api_key.lower().startswith("sk-你的")

    use_real = (
        not force_mock
        and settings.LLM_PROVIDER == "deepseek"
        and bool(api_key)
        and not is_placeholder
    )

    agent_registry._agents.clear()

    if use_real:
        _register_real_agents()
        print(f"[agents] Registered REAL agents (LLM: {settings.LLM_PROVIDER}, model: {settings.DEEPSEEK_MODEL})")
    else:
        from .mock_agents import register_mock_agents
        register_mock_agents()
        if is_placeholder:
            reason = "placeholder API key — replace 'sk-你的密钥' in .env with your real key"
        else:
            reason = "mock mode" if force_mock or settings.LLM_PROVIDER == "mock" else "no API key"
        print(f"[agents] Registered MOCK agents ({reason})")


def _register_real_agents() -> None:
    """Register real agent implementations with tool + LLM integration."""
    from config.loader import load_agents_config
    configs = load_agents_config()

    # Static Analysis Agent (real — uses Semgrep + Pylint + Tree-sitter)
    from .static_analysis.agent import StaticAnalysisAgent
    sa_cfg = configs.get("static_analysis", None)
    sa = StaticAnalysisAgent(
        config=AgentConfig(
            agent_id="static_analysis",
            agent_name="Static Analysis Agent",
            timeout_seconds=sa_cfg.timeout_seconds if sa_cfg else 30,
        )
    )
    agent_registry.register(sa)

    # Semantic Review Agent (real — uses LLM + RAG)
    from .semantic_review.agent import SemanticReviewAgent
    sr_cfg = configs.get("semantic_review", None)
    sr = SemanticReviewAgent(
        config=AgentConfig(
            agent_id="semantic_review",
            agent_name="Semantic Review Agent",
            timeout_seconds=sr_cfg.timeout_seconds if sr_cfg else 60,
        ),
        use_mock_llm=False,
    )
    agent_registry.register(sr)

    # Test & Regression Agent (real)
    from .test_regression.agent import TestRegressionAgent
    tr_cfg = configs.get("test_regression", None)
    tr = TestRegressionAgent(
        config=AgentConfig(
            agent_id="test_regression",
            agent_name="Test & Regression Agent",
            timeout_seconds=tr_cfg.timeout_seconds if tr_cfg else 45,
        ),
        use_mock=False,
    )
    agent_registry.register(tr)

    # Repair & Patch Agent (real)
    from .repair_patch.agent import RepairPatchAgent
    rp_cfg = configs.get("repair_patch", None)
    rp = RepairPatchAgent(
        config=AgentConfig(
            agent_id="repair_patch",
            agent_name="Repair & Patch Agent",
            timeout_seconds=rp_cfg.timeout_seconds if rp_cfg else 60,
        ),
        use_mock=False,
    )
    agent_registry.register(rp)
