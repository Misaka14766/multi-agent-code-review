from pydantic import BaseModel
from .issue import Issue
from .patch import Patch


class QualityGateDecision(BaseModel):
    verdict: str = "pass"
    summary: str = ""
    blocker_count: int = 0
    warning_count: int = 0
    suggestion_count: int = 0
    requires_human: bool = False
    human_questions: list[str] = []


class AgentReport(BaseModel):
    agent_id: str
    agent_name: str = ""
    status: str = ""
    issues_found: int = 0
    execution_time_ms: float = 0.0


class ReviewReport(BaseModel):
    review_id: str
    pr_title: str = ""
    status: str = ""
    quality_gate: QualityGateDecision = QualityGateDecision()
    issues: list[Issue] = []
    patches: list[Patch] = []
    agent_reports: list[AgentReport] = []
    repair_attempts: int = 0
    total_execution_time_ms: float = 0.0
    errors: list[str] = []
