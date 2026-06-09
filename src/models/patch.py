from enum import Enum
from pydantic import BaseModel


class PatchStatus(str, Enum):
    GENERATED = "generated"
    VERIFIED_PASS = "verified_pass"
    VERIFIED_FAIL = "verified_fail"
    APPLIED = "applied"
    REVERTED = "reverted"


class Patch(BaseModel):
    patch_id: str
    issue_ids: list[str] = []
    unified_diff: str
    explanation: str
    files_modified: list[str] = []
    status: PatchStatus = PatchStatus.GENERATED


class PatchVerification(BaseModel):
    patch_id: str
    syntax_check: bool = False
    static_analysis_pass: bool = False
    tests_pass: bool = False
    error_message: str = ""
    status: str = "unverified"
