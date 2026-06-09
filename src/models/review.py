from enum import Enum
from pydantic import BaseModel
from .pr import PRInfo, FileDiff


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    NEEDS_HUMAN = "needs_human"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewRequest(BaseModel):
    code: str | None = None
    file_path: str = "unknown"
    language: str = "python"
    diff_text: str | None = None
    context: str = ""


class ReviewContext(BaseModel):
    review_id: str
    pr_info: PRInfo
    status: ReviewStatus = ReviewStatus.PENDING


class ReviewResponse(BaseModel):
    review_id: str
    status: str
