from typing import TypedDict, Annotated
from pydantic import BaseModel, Field
from src.models.pr import PRInfo, FileDiff
from src.models.issue import Issue
from src.models.patch import Patch, PatchVerification
from src.models.report import QualityGateDecision, AgentReport


def _merge_dicts(a: dict, b: dict) -> dict:
    """Reducer: merge two dicts, with b taking precedence for overlapping keys."""
    merged = dict(a)
    merged.update(b)
    return merged


class ChangeClassification(BaseModel):
    """Categorization of a code change for agent dispatch decisions."""
    primary_type: str = "logic"
    secondary_types: list[str] = []
    affected_modules: list[str] = []
    risk_score: float = Field(ge=0.0, le=1.0, default=0.5)
    recommended_agents: list[str] = []


class AgentAssignment(BaseModel):
    """Mapping of an agent to a review task."""
    agent_id: str
    reason: str = ""
    priority: int = 0


class Conflict(BaseModel):
    """Record of a disagreement between agents that requires resolution."""
    conflict_id: str
    issue_a_id: str
    issue_b_id: str
    description: str = ""
    resolution: str = ""
    resolved_by: str = ""


class RepairResult(BaseModel):
    """Outcome of a repair attempt."""
    patch: Patch | None = None
    verification: PatchVerification | None = None
    success: bool = False


class ReviewState(TypedDict, total=False):
    # --- Input ---
    review_id: str
    pr_info: PRInfo
    code_changes: list[FileDiff]

    # --- Classification ---
    change_classification: ChangeClassification
    agent_assignments: list[AgentAssignment]

    # --- Agent Outputs ---
    static_analysis_issues: list[Issue]
    semantic_review_issues: list[Issue]
    test_regression_issues: list[Issue]

    # --- Arbitration ---
    consolidated_issues: list[Issue]
    conflicts: list[Conflict]

    # --- Quality Gate ---
    quality_gate_decision: QualityGateDecision

    # --- Repair Loop ---
    repair_attempt: int
    current_repair_result: RepairResult
    repair_history: list[RepairResult]

    # --- Report ---
    agent_reports: list[AgentReport]
    final_report: dict
    review_status: str

    # --- Resilience ---
    errors: list[str]
    agent_status: Annotated[dict[str, str], _merge_dicts]
    agent_timing: Annotated[dict[str, float], _merge_dicts]
