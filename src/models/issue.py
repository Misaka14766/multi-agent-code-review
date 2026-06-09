from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    BLOCKER = "blocker"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    INFO = "info"


class IssueType(str, Enum):
    SECURITY = "security"
    BUG = "bug"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    ARCHITECTURE = "architecture"
    TEST_COVERAGE = "test_coverage"


class SourceLocation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    ast_path: str = ""


class CodeReference(BaseModel):
    title: str
    url: str = ""


class Evidence(BaseModel):
    code_snippet: str
    ast_path: str = ""
    similar_bug_refs: list[str] = []


class FixSuggestion(BaseModel):
    unified_diff: str
    explanation: str
    references: list[CodeReference] = []


class Issue(BaseModel):
    issue_id: str
    issue_type: IssueType
    severity: Severity
    title: str
    description: str
    location: SourceLocation
    root_cause: str
    evidence: Evidence
    fix_suggestion: FixSuggestion | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source_agent: str
    verification_status: str = "unverified"
