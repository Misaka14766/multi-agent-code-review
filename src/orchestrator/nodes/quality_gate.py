from ..state import ReviewState, QualityGateDecision


def quality_gate(state: ReviewState) -> ReviewState:
    issues = state.get("consolidated_issues", [])
    repair_attempt = state.get("repair_attempt", 0)

    blockers = [i for i in issues if i.severity.value == "blocker"]
    warnings = [i for i in issues if i.severity.value == "warning"]
    suggestions = [i for i in issues if i.severity.value == "suggestion"]

    blocker_count = len(blockers)
    warning_count = len(warnings)
    suggestion_count = len(suggestions)

    if blocker_count > 0:
        verdict = "blocked"
        summary = f"发现 {blocker_count} 个阻断级缺陷，共 {len(issues)} 个问题。须修复后方可合并。"
    elif warning_count > 0:
        verdict = "needs_fix"
        summary = f"发现 {warning_count} 个警告级问题，共 {len(issues)} 个问题。建议修复后重新审查。"
    else:
        verdict = "pass"
        summary = f"审查通过。发现 {len(issues)} 个建议/信息级问题，可合并。"

    requires_human = any(i.issue_type.value == "security" and i.severity.value in ("blocker", "warning") for i in issues)

    human_questions = []
    if requires_human:
        human_questions.append("安全相关修复需要人工确认后方可应用。")

    decision = QualityGateDecision(
        verdict=verdict,
        summary=summary,
        blocker_count=blocker_count,
        warning_count=warning_count,
        suggestion_count=suggestion_count,
        requires_human=requires_human,
        human_questions=human_questions,
    )

    state["quality_gate_decision"] = decision
    return state
