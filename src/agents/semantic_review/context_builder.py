"""Build review context for the Semantic Review Agent from code + RAG results."""

from src.models.pr import PRInfo, FileDiff
from src.knowledge.schemas import RetrievalResult

MAX_CONTEXT_CHARS = 8000


def build_review_context(pr_info: PRInfo, rag_results: list[RetrievalResult] | None = None) -> dict:
    """Assemble the full context dictionary for the LLM review prompt."""
    rag_results = rag_results or []

    # Extract code from changed files
    code_snippets: list[dict] = []
    for f in pr_info.files_changed:
        content = f.new_content or f.old_content or ""
        if len(content) > MAX_CONTEXT_CHARS // max(len(pr_info.files_changed), 1):
            content = content[:MAX_CONTEXT_CHARS // max(len(pr_info.files_changed), 1)] + "\n# ... (truncated)"
        code_snippets.append({
            "file_path": f.file_path,
            "language": f.language,
            "content": content,
        })

    # Extract relevant coding standards from RAG results
    conventions: list[str] = []
    similar_bugs: list[dict] = []
    for r in rag_results:
        if r.document.knowledge_type.value in ("coding_standard", "architecture_rule"):
            conventions.append(r.document.content[:200])
        elif r.document.knowledge_type.value in ("bug_pattern", "review_experience"):
            similar_bugs.append({
                "title": r.document.title,
                "root_cause": r.document.content[:300],
                "similarity": r.similarity_score,
                "fix": r.document.metadata.get("fix", ""),
            })

    return {
        "code_snippets": code_snippets,
        "conventions": conventions,
        "similar_bugs": similar_bugs,
        "total_changed_files": len(pr_info.files_changed),
        "pr_title": pr_info.title,
        "pr_description": pr_info.description,
    }
