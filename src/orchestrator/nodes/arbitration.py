from ..state import ReviewState, Conflict
from src.models.issue import Issue


def _location_key(issue: Issue) -> str:
    return f"{issue.location.file_path}:{issue.location.start_line}"


def arbitrate(state: ReviewState) -> ReviewState:
    all_issues: list[Issue] = []
    all_issues.extend(state.get("static_analysis_issues", []))
    all_issues.extend(state.get("semantic_review_issues", []))
    all_issues.extend(state.get("test_regression_issues", []))

    if not all_issues:
        state["consolidated_issues"] = []
        state["conflicts"] = []
        return state

    # Deduplicate by location
    seen: dict[str, Issue] = {}
    conflicts: list[Conflict] = []

    for issue in all_issues:
        key = _location_key(issue)
        if key in seen:
            existing = seen[key]
            # Keep the one with higher confidence
            if issue.confidence > existing.confidence:
                conflicts.append(Conflict(
                    conflict_id=f"CONFLICT-{len(conflicts)+1:03d}",
                    issue_a_id=existing.issue_id,
                    issue_b_id=issue.issue_id,
                    description=f"Agents disagree on severity/confidence at {key}",
                    resolution="rule_based",
                    resolved_by="arbitration_node",
                ))
                seen[key] = issue
            else:
                conflicts.append(Conflict(
                    conflict_id=f"CONFLICT-{len(conflicts)+1:03d}",
                    issue_a_id=issue.issue_id,
                    issue_b_id=existing.issue_id,
                    description=f"Agents disagree on severity/confidence at {key}",
                    resolution="rule_based",
                    resolved_by="arbitration_node",
                ))
        else:
            seen[key] = issue

    # Sort: blocker first, then by confidence descending
    severity_order = {"blocker": 0, "warning": 1, "suggestion": 2, "info": 3}
    consolidated = sorted(seen.values(), key=lambda i: (severity_order.get(i.severity.value, 2), -i.confidence))

    state["consolidated_issues"] = consolidated
    state["conflicts"] = conflicts
    return state
