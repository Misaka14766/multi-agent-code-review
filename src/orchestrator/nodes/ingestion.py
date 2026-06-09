from ..state import ReviewState


def ingest_pr(state: ReviewState) -> ReviewState:
    pr_info = state["pr_info"]
    files = pr_info.files_changed

    state["code_changes"] = files
    state["review_status"] = "in_progress"

    if not files:
        state["errors"] = state.get("errors", []) + ["No files to review"]

    return state
