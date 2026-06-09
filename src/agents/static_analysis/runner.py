"""Process management utilities for external tools."""

import asyncio
import logging
from src.tools.base import ToolResult, StructuredResult, ToolInterface

logger = logging.getLogger(__name__)


async def run_tool_with_fallback(
    tool: ToolInterface,
    context: dict,
    fallback_result: StructuredResult | None = None,
) -> StructuredResult:
    """Run a tool with timeout. Return fallback on failure; never raise."""
    try:
        return await tool.run_full_pipeline(context)
    except asyncio.TimeoutError:
        logger.warning("Tool '%s' timed out", tool.tool_name)
    except FileNotFoundError:
        logger.warning("Tool '%s' not installed", tool.tool_name)
    except Exception as e:
        logger.warning("Tool '%s' failed: %s", tool.tool_name, e)

    if fallback_result is not None:
        return fallback_result
    return StructuredResult(
        tool_name=tool.tool_name,
        findings=[],
        summary=f"{tool.tool_name} unavailable",
    )


async def run_all_tools(
    tools: list[ToolInterface],
    context: dict,
) -> list[StructuredResult]:
    """Run multiple tools in parallel, collecting all results."""
    tasks = [run_tool_with_fallback(t, context) for t in tools]
    return await asyncio.gather(*tasks)
