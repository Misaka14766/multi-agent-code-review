from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from src.models.issue import Issue
from src.models.pr import PRInfo


@dataclass
class AgentCapability:
    change_types: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    agent_id: str
    agent_name: str
    enabled: bool = True
    timeout_seconds: int = 30


@dataclass
class AgentResult:
    agent_id: str
    status: str = "success"
    issues: list[Issue] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error_message: str = ""
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @abstractmethod
    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        ...

    @abstractmethod
    def get_capability(self) -> AgentCapability:
        ...

    def can_handle(self, change_type: str) -> bool:
        cap = self.get_capability()
        return change_type in cap.change_types

    async def health_check(self) -> bool:
        return self.config.enabled


class AgentRegistry:
    """Registry for agent instances. Use the module-level `agent_registry` singleton."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def list_all(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def get_by_capability(self, change_type: str) -> list[BaseAgent]:
        return [a for a in self._agents.values() if a.can_handle(change_type)]

    async def health_check_all(self) -> dict[str, bool]:
        results = {}
        for aid, agent in self._agents.items():
            results[aid] = await agent.health_check()
        return results


agent_registry = AgentRegistry()
