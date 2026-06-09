"""Tool registry — singleton for tool lookup by name."""

from .base import ToolInterface


class ToolRegistry:
    """Registry of available tools, keyed by tool_name."""

    def __init__(self):
        self._tools: dict[str, ToolInterface] = {}

    def register(self, tool: ToolInterface) -> None:
        self._tools[tool.tool_name] = tool

    def get(self, tool_name: str) -> ToolInterface | None:
        return self._tools.get(tool_name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def is_available(self, tool_name: str) -> bool:
        return tool_name in self._tools


tool_registry = ToolRegistry()
