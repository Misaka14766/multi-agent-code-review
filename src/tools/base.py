"""Tool abstraction layer — unified interface for all external analysis tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolPlan:
    """Decision record: whether and how to invoke a tool."""
    tool_name: str
    parameters: dict = field(default_factory=dict)
    reason: str = ""
    timeout_seconds: int = 60


@dataclass
class ToolResult:
    """Raw output from a tool execution."""
    tool_name: str
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0


@dataclass
class StructuredResult:
    """Parsed, structured output that agents can consume."""
    tool_name: str
    findings: list[dict] = field(default_factory=list)
    summary: str = ""
    raw: ToolResult | None = None


class ToolInterface(ABC):
    """Unified interface for all external tools (Semgrep, Pylint, Tree-sitter, etc.)."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    @abstractmethod
    async def plan(self, context: dict) -> ToolPlan:
        """Decide whether and how to invoke the tool based on context."""
        ...

    @abstractmethod
    async def execute(self, plan: ToolPlan) -> ToolResult:
        """Run the tool (subprocess, HTTP call, etc.)."""
        ...

    @abstractmethod
    def parse(self, raw: ToolResult) -> StructuredResult:
        """Convert raw tool output to structured data."""
        ...

    @abstractmethod
    async def validate(self, result: StructuredResult) -> bool:
        """Verify result integrity (no empty output, parse errors, etc.)."""
        ...

    async def run_full_pipeline(self, context: dict) -> StructuredResult:
        """Convenience: plan → execute → parse → validate in one call."""
        plan = await self.plan(context)
        raw = await self.execute(plan)
        result = self.parse(raw)
        valid = await self.validate(result)
        if not valid:
            result.summary = f"[VALIDATION FAILED] {result.summary}"
        return result
