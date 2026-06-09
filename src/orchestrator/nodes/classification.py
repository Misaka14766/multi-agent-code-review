import os
from pathlib import Path

from ..state import ReviewState, ChangeClassification, AgentAssignment

LANGUAGE_TO_CHANGE_TYPE = {
    "sql": "security",
    "auth": "security",
    "login": "security",
    "password": "security",
    "token": "security",
    "api": "logic",
    "service": "logic",
    "controller": "logic",
    "model": "logic",
    "test": "test",
    "config": "config",
    "component": "ui",
    "style": "ui",
    "css": "ui",
    "doc": "docs",
    "readme": "docs",
    "util": "refactor",
    "helper": "refactor",
    "package": "dependency",
    "requirements": "dependency",
}


def classify_changes(state: ReviewState) -> ReviewState:
    files = state.get("code_changes", [])
    if not files:
        state["change_classification"] = ChangeClassification()
        state["agent_assignments"] = []
        return state

    types_seen: set[str] = set()
    modules: set[str] = set()

    for f in files:
        path_lower = f.file_path.lower()
        for keyword, ctype in LANGUAGE_TO_CHANGE_TYPE.items():
            if keyword in path_lower:
                types_seen.add(ctype)
        parts = Path(f.file_path).parts
        module = parts[0] if parts else path_lower.split(".")[0]
        modules.add(module)

    types_list = list(types_seen) if types_seen else ["logic"]
    primary = types_list[0]
    secondary = types_list[1:] if len(types_list) > 1 else []

    risk_score = 0.5
    if "security" in types_seen:
        risk_score = 0.85
    elif "logic" in types_seen:
        risk_score = 0.6
    elif "test" in types_seen or "docs" in types_seen:
        risk_score = 0.2

    classification = ChangeClassification(
        primary_type=primary,
        secondary_types=secondary,
        affected_modules=list(modules),
        risk_score=risk_score,
        recommended_agents=["static_analysis", "semantic_review", "test_regression"],
    )

    assignments = []
    agent_map = {
        "security": ["static_analysis", "semantic_review", "test_regression"],
        "logic": ["static_analysis", "semantic_review", "test_regression"],
        "bug": ["static_analysis", "semantic_review"],
        "style": ["static_analysis"],
        "performance": ["semantic_review", "test_regression"],
        "architecture": ["semantic_review"],
        "config": ["static_analysis"],
        "test": ["test_regression"],
        "docs": [],
        "refactor": ["static_analysis", "semantic_review"],
        "dependency": ["static_analysis"],
        "ui": ["static_analysis"],
    }

    dispatch_agents: set[str] = set()
    for t in types_list:
        for agent_id in agent_map.get(t, []):
            dispatch_agents.add(agent_id)

    if not dispatch_agents:
        dispatch_agents = {"static_analysis", "semantic_review"}

    for i, agent_id in enumerate(sorted(dispatch_agents)):
        assignments.append(AgentAssignment(agent_id=agent_id, reason=f"Matched change type: {primary}", priority=i))

    state["change_classification"] = classification
    state["agent_assignments"] = assignments
    return state
