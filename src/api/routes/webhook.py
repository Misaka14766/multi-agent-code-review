"""GitHub webhook receiver."""

import hashlib
import hmac
import json
import uuid
import logging

from fastapi import APIRouter, Request, HTTPException, Header, Depends, BackgroundTasks

from src.api.deps import get_orchestrator, get_settings
from src.orchestrator.graph import ReviewOrchestrator
from src.models.pr import PRInfo, FileDiff

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    orchestrator: ReviewOrchestrator = Depends(get_orchestrator),
):
    """Receive PR events from GitHub and trigger reviews."""
    settings = get_settings()
    body = await request.body()

    # Validate HMAC signature if secret is configured
    if settings.GITHUB_WEBHOOK_SECRET:
        expected = "sha256=" + hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256 or ""):
            raise HTTPException(status_code=403, detail="Invalid signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if event_type == "ping":
        return {"status": "ok", "message": "Webhook configured successfully"}

    if event_type == "pull_request" and payload.get("action") in ("opened", "synchronize"):
        pr_data = payload.get("pull_request", {})
        review_id = uuid.uuid4().hex[:8]

        # Extract file changes (simplified — real impl would use GitHub API)
        files_changed: list[FileDiff] = []
        try:
            head_sha = pr_data.get("head", {}).get("sha", "")
            if head_sha:
                files_changed.append(FileDiff(
                    file_path=f"PR #{pr_data.get('number', '?')}",
                    change_type="modified",
                    diff_text=f"PR diff for {head_sha[:8]}",
                    language="unknown",
                ))
        except Exception:
            pass

        pr_info = PRInfo(
            pr_id=review_id,
            title=pr_data.get("title", "Untitled PR"),
            description=pr_data.get("body", "") or "",
            repo_url=pr_data.get("base", {}).get("repo", {}).get("html_url", ""),
            base_branch=pr_data.get("base", {}).get("ref", "main"),
            head_branch=pr_data.get("head", {}).get("ref", ""),
            author=pr_data.get("user", {}).get("login", ""),
            files_changed=files_changed,
            files_count=pr_data.get("changed_files", len(files_changed)),
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
        )

        background_tasks.add_task(orchestrator.run_review, review_id, pr_info)
        logger.info("Webhook: PR #%s review queued as %s", pr_data.get("number"), review_id)
        return {"review_id": review_id, "status": "accepted", "pr_number": pr_data.get("number")}

    return {"status": "ignored", "event": event_type}
