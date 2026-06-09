"""Real Repair & Patch Agent — auto-generate and verify code fix patches."""

import logging
import time

from src.agents.base import BaseAgent, AgentConfig, AgentCapability, AgentResult
from src.models.pr import PRInfo
from src.models.issue import Issue
from src.models.patch import Patch, PatchStatus
from .generator import generate_patches
from .verifier import verify_patch

logger = logging.getLogger(__name__)


class RepairPatchAgent(BaseAgent):
    """Generates unified-diff patches for reported issues and verifies them.

    Pipeline:
      1. Receive consolidated blocker/warning issues
      2. Generate patches via LLM (mock or real)
      3. Verify each patch: syntax → static analysis → sandbox tests
    """

    def __init__(self, config: AgentConfig | None = None, use_mock: bool = True):
        cfg = config or AgentConfig(agent_id="repair_patch", agent_name="Repair & Patch Agent", timeout_seconds=60)
        super().__init__(cfg)
        self.use_mock = use_mock
        self._patch_history: set[str] = set()  # Track generated patches to avoid duplicates

    def get_capability(self) -> AgentCapability:
        return AgentCapability(
            change_types=["security", "bug", "performance", "style"],
            languages=["python", "javascript", "typescript"],
            produces=["patches"],
        )

    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        start = time.time()
        context = context or {}

        target_issues: list[Issue] = context.get("target_issues", [])
        if not target_issues:
            return AgentResult(agent_id=self.agent_id, status="success", issues=[], execution_time_ms=0,
                             metadata={"patches": [], "message": "No issues to repair"})

        # Build issue dicts for the generator
        issue_dicts = [
            {
                "id": i.issue_id,
                "issue_id": i.issue_id,
                "title": i.title,
                "root_cause": i.root_cause,
                "file_path": i.location.file_path,
                "line": i.location.start_line,
                "severity": i.severity.value,
            }
            for i in target_issues
        ]

        all_patches: list[dict] = []
        verified_patches: list[Patch] = []

        # Generate per-file patches
        files_seen: set[str] = set()
        for f in pr_info.files_changed:
            if f.file_path in files_seen:
                continue
            files_seen.add(f.file_path)
            code = f.new_content or f.old_content or ""
            if not code.strip():
                continue

            file_issues = [i for i in issue_dicts if i["file_path"] == f.file_path or not i["file_path"]]
            if not file_issues:
                file_issues = issue_dicts  # All issues if no file match

            try:
                patches_data = await generate_patches(
                    original_code=code,
                    file_path=f.file_path,
                    issues=file_issues,
                    use_mock=self.use_mock,
                )
            except Exception as e:
                logger.warning("Patch generation failed for %s: %s", f.file_path, e)
                continue

            for pdata in patches_data:
                patch_id = pdata.get("patch_id", f"PATCH-{len(all_patches)+1:03d}")

                # Skip duplicate patches
                diff_key = pdata.get("unified_diff", "")[:200]
                if diff_key in self._patch_history:
                    continue
                self._patch_history.add(diff_key)

                patch = Patch(
                    patch_id=patch_id,
                    issue_ids=pdata.get("issue_ids", []),
                    unified_diff=pdata.get("unified_diff", ""),
                    explanation=pdata.get("explanation", ""),
                    files_modified=pdata.get("files_modified", [f.file_path]),
                    status=PatchStatus.GENERATED,
                )

                # Verify the patch
                try:
                    verification = await verify_patch(patch, code)
                    patch.verification_status = verification.status  # type: ignore[assignment]
                    if verification.status == "verified_pass":
                        patch.status = PatchStatus.VERIFIED_PASS
                except Exception as e:
                    logger.warning("Patch verification failed: %s", e)

                verified_patches.append(patch)
                all_patches.append(pdata)

        elapsed = (time.time() - start) * 1000
        return AgentResult(
            agent_id=self.agent_id,
            status="success",
            issues=[],
            execution_time_ms=elapsed,
            metadata={
                "patches": all_patches,
                "verified": len([p for p in verified_patches if p.status == PatchStatus.VERIFIED_PASS]),
                "total": len(verified_patches),
                "files_modified": list(files_seen),
                "llm_mode": "mock" if self.use_mock else "deepseek",
            },
        )
