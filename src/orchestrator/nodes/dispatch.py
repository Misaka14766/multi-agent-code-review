from langgraph.types import Send
from ..state import ReviewState


def dispatch_to_agents(state: ReviewState) -> list[Send]:
    assignments = state.get("agent_assignments", [])
    if not assignments:
        return []

    # Pass pr_info so agents can read it. Agents return partial dicts (only their own
    # issue key + agent_status/agent_reports/errors with reducers), so pr_info won't conflict.
    sends = []
    for assignment in assignments:
        sends.append(Send(assignment.agent_id, {"pr_info": state["pr_info"]}))
    return sends
