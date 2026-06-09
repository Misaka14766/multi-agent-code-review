"""LangGraph state machine for the multi-agent code review pipeline."""

import time
from langgraph.graph import StateGraph, END
from .state import ReviewState, ChangeClassification, RepairResult
from .nodes.ingestion import ingest_pr
from .nodes.classification import classify_changes
from .nodes.dispatch import dispatch_to_agents
from .nodes.agent_workers import static_analysis, semantic_review, test_regression, repair, verify_repair
from .nodes.arbitration import arbitrate
from .nodes.quality_gate import quality_gate
from .nodes.reporting import generate_report
from .conditions import needs_repair, repair_loop_decision

MAX_ACTIVE_REVIEWS = 100
REVIEW_TTL_SECONDS = 3600


def build_review_graph() -> StateGraph:
    """Build and compile the review workflow as a LangGraph StateGraph."""
    builder = StateGraph(ReviewState)

    # Register all nodes
    builder.add_node("ingest_pr", ingest_pr)
    builder.add_node("classify_changes", classify_changes)
    builder.add_node("static_analysis", static_analysis)
    builder.add_node("semantic_review", semantic_review)
    builder.add_node("test_regression", test_regression)
    builder.add_node("arbitrate", arbitrate)
    builder.add_node("quality_gate", quality_gate)
    builder.add_node("repair", repair)
    builder.add_node("verify_repair", verify_repair)
    builder.add_node("generate_report", generate_report)

    # Entry point
    builder.set_entry_point("ingest_pr")

    # Sequential: ingest → classify
    builder.add_edge("ingest_pr", "classify_changes")

    # Parallel fan-out: classify → [static_analysis, semantic_review, test_regression]
    builder.add_conditional_edges(
        "classify_changes",
        dispatch_to_agents,
        ["static_analysis", "semantic_review", "test_regression"],
    )

    # All agents converge at arbitrate
    builder.add_edge("static_analysis", "arbitrate")
    builder.add_edge("semantic_review", "arbitrate")
    builder.add_edge("test_regression", "arbitrate")

    # Arbitrate → quality gate
    builder.add_edge("arbitrate", "quality_gate")

    # Quality gate branches: repair or finish
    builder.add_conditional_edges(
        "quality_gate",
        needs_repair,
        {"repair": "repair", "generate_report": "generate_report"},
    )

    # Repair → verify → decide next
    builder.add_edge("repair", "verify_repair")
    builder.add_conditional_edges(
        "verify_repair",
        repair_loop_decision,
        {"generate_report": "generate_report"},
    )

    # Report is terminal
    builder.add_edge("generate_report", END)

    return builder.compile()


def _make_initial_state(review_id: str, pr_info) -> ReviewState:
    """Create the initial ReviewState for a new review."""
    return {
        "review_id": review_id,
        "pr_info": pr_info,
        "code_changes": pr_info.files_changed,
        "change_classification": ChangeClassification(),
        "agent_assignments": [],
        "static_analysis_issues": [],
        "semantic_review_issues": [],
        "test_regression_issues": [],
        "consolidated_issues": [],
        "conflicts": [],
        "quality_gate_decision": None,  # type: ignore[typeddict-item]
        "repair_attempt": 0,
        "current_repair_result": RepairResult(success=False),
        "repair_history": [],
        "agent_reports": [],
        "final_report": {},
        "review_status": "pending",
        "errors": [],
        "agent_status": {},
        "agent_timing": {},
    }


class ReviewOrchestrator:
    """Central coordinator that manages review lifecycle and graph execution."""

    def __init__(self):
        self.graph = build_review_graph()
        self._active_reviews: dict[str, tuple[ReviewState, float]] = {}

    async def run_review(self, review_id: str, pr_info) -> dict:
        """Execute a full review pipeline and return the final report dict."""
        initial_state = _make_initial_state(review_id, pr_info)
        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception:
            final_state = initial_state
            final_state["review_status"] = "failed"
            final_state["errors"] = final_state.get("errors", []) + ["Graph execution failed"]
        self._active_reviews[review_id] = (final_state, time.time())
        self._evict_old_reviews()
        return final_state.get("final_report", {})

    def get_review_state(self, review_id: str) -> ReviewState | None:
        """Return the stored state for a completed review, or None."""
        entry = self._active_reviews.get(review_id)
        return entry[0] if entry else None

    def _evict_old_reviews(self) -> None:
        """Remove reviews past TTL, keeping at most MAX_ACTIVE_REVIEWS."""
        now = time.time()
        expired = [
            rid for rid, (_, ts) in self._active_reviews.items()
            if now - ts > REVIEW_TTL_SECONDS
        ]
        for rid in expired:
            del self._active_reviews[rid]
        if len(self._active_reviews) > MAX_ACTIVE_REVIEWS:
            oldest = sorted(self._active_reviews.items(), key=lambda x: x[1][1])
            for rid, _ in oldest[:len(self._active_reviews) - MAX_ACTIVE_REVIEWS]:
                del self._active_reviews[rid]
