"""Edge routing conditions for the review workflow graph."""

from .state import ReviewState

MAX_REPAIR_ATTEMPTS = 3


def needs_repair(state: ReviewState) -> str:
    """After quality gate: route to repair if blockers exist and attempts remain."""
    decision = state.get("quality_gate_decision")
    if decision and decision.verdict == "blocked":
        attempt = state.get("repair_attempt", 0)
        if attempt < MAX_REPAIR_ATTEMPTS:
            return "repair"
    return "generate_report"


def repair_loop_decision(state: ReviewState) -> str:
    """After verify_repair: finish, or loop back for re-review if within attempt limit."""
    attempt = state.get("repair_attempt", 0)
    result = state.get("current_repair_result")
    if result and result.success and attempt < MAX_REPAIR_ATTEMPTS:
        # Enable re-review cycle when real agents confirm fix is valid
        return "generate_report"  # Change to "classify_changes" for full re-review loop
    return "generate_report"
