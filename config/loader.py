"""Load agent configuration from YAML and provide typed access."""

from pathlib import Path
from dataclasses import dataclass, field
import yaml


@dataclass
class AgentYAMLConfig:
    enabled: bool = True
    timeout_seconds: int = 30
    tools: list[str] = field(default_factory=list)
    model: str = ""
    temperature: float = 0.1
    rag: dict = field(default_factory=dict)


def load_agents_config(path: Path | str | None = None) -> dict[str, AgentYAMLConfig]:
    """Parse config/agents.yaml and return a dict of agent_id -> AgentYAMLConfig."""
    if path is None:
        path = Path(__file__).parent / "agents.yaml"
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    configs: dict[str, AgentYAMLConfig] = {}
    for agent_id, data in raw.get("agents", {}).items():
        configs[agent_id] = AgentYAMLConfig(
            enabled=data.get("enabled", True),
            timeout_seconds=data.get("timeout_seconds", 30),
            tools=data.get("tools", []),
            model=data.get("model", ""),
            temperature=data.get("temperature", 0.1),
            rag=data.get("rag", {}),
        )
    return configs
