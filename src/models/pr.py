from enum import Enum
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    SECURITY = "security"
    LOGIC = "logic"
    CONFIG = "config"
    UI = "ui"
    TEST = "test"
    DOCS = "docs"
    REFACTOR = "refactor"
    DEPENDENCY = "dependency"


class FileDiff(BaseModel):
    file_path: str
    change_type: str = "modified"
    old_content: str | None = None
    new_content: str | None = None
    diff_text: str = ""
    language: str = ""


class PRInfo(BaseModel):
    pr_id: str
    title: str
    description: str = ""
    repo_url: str = ""
    base_branch: str = "main"
    head_branch: str = ""
    author: str = ""
    files_changed: list[FileDiff] = []
    files_count: int = 0
    additions: int = 0
    deletions: int = 0
    labels: list[str] = []
