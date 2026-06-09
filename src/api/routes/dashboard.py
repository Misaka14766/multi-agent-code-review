"""Dashboard API — aggregate statistics for the web UI."""

from fastapi import APIRouter, Depends
from src.api.deps import get_orchestrator
from src.orchestrator.graph import ReviewOrchestrator

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(orchestrator: ReviewOrchestrator = Depends(get_orchestrator)):
    """Return aggregate review statistics for the dashboard."""
    total = len(orchestrator._active_reviews)
    blocked = 0
    passed = 0
    total_issues = 0
    total_patches = 0

    for _, (state, _) in orchestrator._active_reviews.items():
        report = state.get("final_report", {})
        if not report:
            continue
        verdict = report.get("summary", {}).get("verdict", "")
        if verdict == "blocked":
            blocked += 1
        elif verdict == "pass":
            passed += 1
        total_issues += report.get("summary", {}).get("total_issues", 0)
        total_patches += len(report.get("patches", []))

    return {
        "total_reviews": total,
        "blocked": blocked,
        "passed": passed,
        "pending": total - blocked - passed,
        "total_issues_found": total_issues,
        "total_patches_generated": total_patches,
    }


@router.get("/history")
async def get_history(limit: int = 10, orchestrator: ReviewOrchestrator = Depends(get_orchestrator)):
    """Return recent review history."""
    history = []
    for review_id, (state, ts) in sorted(
        orchestrator._active_reviews.items(),
        key=lambda x: x[1][1],
        reverse=True,
    )[:limit]:
        report = state.get("final_report", {})
        summary = report.get("summary", {})
        history.append({
            "review_id": review_id,
            "verdict": summary.get("verdict", "pending"),
            "issues": summary.get("total_issues", 0),
            "pr_title": report.get("pr_title", ""),
        })
    return {"reviews": history}
