from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    content: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], **kwargs) -> LLMResponse:
        ...

    async def complete_stream(self, messages: list[dict], **kwargs):
        raise NotImplementedError("Streaming not supported by this client")
