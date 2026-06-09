"""Data models for the RAG knowledge layer."""

from enum import Enum
from pydantic import BaseModel, Field


class KnowledgeType(str, Enum):
    CODING_STANDARD = "coding_standard"
    BUG_PATTERN = "bug_pattern"
    ARCHITECTURE_RULE = "architecture_rule"
    REVIEW_EXPERIENCE = "review_experience"
    API_USAGE = "api_usage"


class KnowledgeDocument(BaseModel):
    doc_id: str
    knowledge_type: KnowledgeType
    title: str
    content: str
    metadata: dict = {}
    source_issue_id: str | None = None
    embedding: list[float] | None = None


class RetrievalResult(BaseModel):
    document: KnowledgeDocument
    similarity_score: float = Field(ge=0.0, le=1.0)
    retrieval_method: str = "vector"


class SearchQuery(BaseModel):
    query_text: str
    knowledge_types: list[KnowledgeType] | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)
