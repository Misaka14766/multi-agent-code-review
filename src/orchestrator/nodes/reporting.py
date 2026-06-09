from ..state import ReviewState, AgentReport


def generate_report(state: ReviewState) -> ReviewState:
    issues = state.get("consolidated_issues", [])
    decision = state.get("quality_gate_decision")
    agent_status = state.get("agent_status", {})
    agent_timing = state.get("agent_timing", {})
    repair_attempt = state.get("repair_attempt", 0)

    # Build agent reports from what we know
    agent_reports: list[AgentReport] = []
    agent_names = {
        "static_analysis": "Static Analysis Agent",
        "semantic_review": "Semantic Review Agent",
        "test_regression": "Test & Regression Agent",
        "repair_patch": "Repair & Patch Agent",
    }
    for aid, status in agent_status.items():
        agent_issues = [i for i in issues if i.source_agent == aid]
        agent_reports.append(AgentReport(
            agent_id=aid,
            agent_name=agent_names.get(aid, aid),
            status=status,
            issues_found=len(agent_issues),
            execution_time_ms=agent_timing.get(aid, 0.0),
        ))

    blocker_count = sum(1 for i in issues if i.severity.value == "blocker")
    warning_count = sum(1 for i in issues if i.severity.value == "warning")
    suggestion_count = sum(1 for i in issues if i.severity.value == "suggestion")
    info_count = sum(1 for i in issues if i.severity.value == "info")

    total_time = sum(r.execution_time_ms for r in agent_reports)

    # Collect patches from repair history
    patches_data = []
    for repair_result in state.get("repair_history", []):
        if repair_result.patch:
            patches_data.append(repair_result.patch.model_dump())

    report = {
        "review_id": state.get("review_id", ""),
        "pr_title": state.get("pr_info", None) and state["pr_info"].title or "",
        "status": "completed",
        "summary": {
            "total_issues": len(issues),
            "blockers": blocker_count,
            "warnings": warning_count,
            "suggestions": suggestion_count,
            "info": info_count,
            "verdict": decision.verdict if decision else "unknown",
            "verdict_summary": decision.summary if decision else "",
            "requires_human": decision.requires_human if decision else False,
            "repair_attempts": repair_attempt,
            "total_execution_time_ms": total_time,
        },
        "quality_gate": decision.model_dump() if decision else {},
        "issues": [i.model_dump() for i in issues],
        "patches": patches_data,
        "agent_reports": [r.model_dump() for r in agent_reports],
        "errors": state.get("errors", []),
        "human_questions": decision.human_questions if decision else [],
    }

    state["final_report"] = report
    state["review_status"] = "completed"
    return state
