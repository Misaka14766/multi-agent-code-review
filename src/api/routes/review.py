"""Review API routes — submit code and retrieve results."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.api.deps import get_orchestrator
from src.orchestrator.graph import ReviewOrchestrator
from src.models.pr import PRInfo, FileDiff

router = APIRouter(prefix="/api/v1/review", tags=["review"])


class ReviewRequest(BaseModel):
    code: str
    file_path: str = "input.py"
    language: str = "python"
    context: str = ""


class ReviewResponse(BaseModel):
    review_id: str
    status: str
    message: str = ""


@router.post("", response_model=ReviewResponse)
async def submit_review(
    request: ReviewRequest,
    background_tasks: BackgroundTasks,
    orchestrator: ReviewOrchestrator = Depends(get_orchestrator),
):
    """Submit code for review. Returns immediately; review runs asynchronously."""
    review_id = uuid.uuid4().hex[:8]
    pr_info = PRInfo(
        pr_id=review_id,
        title=f"Review: {request.file_path}",
        description=request.context,
        files_changed=[
            FileDiff(
                file_path=request.file_path,
                change_type="modified",
                new_content=request.code,
                language=request.language,
            )
        ],
        files_count=1,
        additions=request.code.count("\n") + 1,
        deletions=0,
    )
    background_tasks.add_task(orchestrator.run_review, review_id, pr_info)
    return ReviewResponse(review_id=review_id, status="pending", message="Review started")


@router.get("/{review_id}")
async def get_review_status(
    review_id: str,
    orchestrator: ReviewOrchestrator = Depends(get_orchestrator),
):
    """Get the current status of a review."""
    state = orchestrator.get_review_state(review_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return {
        "review_id": review_id,
        "status": state.get("review_status", "unknown"),
        "errors": state.get("errors", []),
    }


@router.get("/{review_id}/report")
async def get_review_report(
    review_id: str,
    orchestrator: ReviewOrchestrator = Depends(get_orchestrator),
):
    """Get the complete review report."""
    state = orchestrator.get_review_state(review_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Review not found")
    report = state.get("final_report", {})
    if not report:
        raise HTTPException(status_code=202, detail="Review not yet completed")
    return report
