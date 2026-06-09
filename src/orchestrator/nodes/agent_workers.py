import asyncio
from ..state import ReviewState
from src.agents.base import agent_registry


async def _run_agent(state: ReviewState, agent_id: str, output_key: str) -> dict:
    """Run a single agent with timeout, returning a partial state update dict."""
    import time
    from config.settings import settings

    agent = agent_registry.get(agent_id)
    result_dict: dict = {}

    if not agent:
        result_dict["agent_status"] = {agent_id: "not_found"}
        return result_dict

    start = time.time()
    try:
        result = await asyncio.wait_for(
            agent.analyze(state["pr_info"]),
            timeout=settings.AGENT_TIMEOUT_SECONDS,
        )
        elapsed = (time.time() - start) * 1000
        result_dict[output_key] = result.issues
        result_dict["agent_status"] = {agent_id: result.status}
        result_dict["agent_timing"] = {agent_id: elapsed}
    except asyncio.TimeoutError:
        result_dict[output_key] = []
        result_dict["agent_status"] = {agent_id: "timeout"}
        result_dict["errors"] = [f"{agent_id} timed out"]
    except Exception as e:
        result_dict[output_key] = []
        result_dict["agent_status"] = {agent_id: "error"}
        result_dict["errors"] = [f"{agent_id} failed: {e}"]

    return result_dict


async def static_analysis(state: ReviewState) -> ReviewState:
    return await _run_agent(state, "static_analysis", "static_analysis_issues")


async def semantic_review(state: ReviewState) -> ReviewState:
    return await _run_agent(state, "semantic_review", "semantic_review_issues")


async def test_regression(state: ReviewState) -> ReviewState:
    return await _run_agent(state, "test_regression", "test_regression_issues")


async def repair(state: ReviewState) -> ReviewState:
    from src.agents.base import agent_registry
    from ..state import RepairResult

    agent = agent_registry.get("repair_patch")
    if not agent:
        state["current_repair_result"] = RepairResult(success=False)
        return state

    attempt = state.get("repair_attempt", 0) + 1
    target_issues = [i for i in state.get("consolidated_issues", []) if i.severity.value == "blocker"]
    if not target_issues:
        target_issues = state.get("consolidated_issues", [])

    context = {"target_issues": target_issues, "pr_info": state["pr_info"]}

    try:
        result = await asyncio.wait_for(agent.analyze(state["pr_info"], context), timeout=60)
        patches_data = result.metadata.get("patches", [])
        from src.models.patch import Patch, PatchStatus
        patches = []
        for p in patches_data:
            patches.append(Patch(
                patch_id=p.get("patch_id", ""),
                issue_ids=p.get("issue_ids", []),
                unified_diff=p.get("unified_diff", ""),
                explanation=p.get("explanation", ""),
                files_modified=p.get("files_modified", []),
                status=PatchStatus.GENERATED,
            ))
        state["current_repair_result"] = RepairResult(
            patch=patches[0] if patches else None,
            success=len(patches) > 0,
        )
    except Exception as e:
        state["current_repair_result"] = RepairResult(success=False)
        state["errors"] = state.get("errors", []) + [f"Repair failed: {e}"]

    state["repair_attempt"] = attempt
    history = state.get("repair_history", [])
    history.append(state["current_repair_result"])
    state["repair_history"] = history
    return state


async def verify_repair(state: ReviewState) -> ReviewState:
    from ..state import RepairResult
    result = state.get("current_repair_result", RepairResult(success=False))

    # Mock verification: simulate syntax check + test run
    if result.patch:
        from src.models.patch import PatchVerification
        result.verification = PatchVerification(
            patch_id=result.patch.patch_id,
            syntax_check=True,
            static_analysis_pass=True,
            tests_pass=True,
            status="verified_pass",
        )
        result.success = True
    else:
        result.success = False

    state["current_repair_result"] = result
    return state
