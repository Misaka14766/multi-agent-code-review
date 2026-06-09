"""Tests for knowledge layer data models."""
from src.knowledge.schemas import KnowledgeDocument, KnowledgeType, SearchQuery, RetrievalResult


class TestKnowledgeDocument:
    def test_create_document(self):
        doc = KnowledgeDocument(
            doc_id="TEST-001",
            knowledge_type=KnowledgeType.BUG_PATTERN,
            title="SQL Injection",
            content="Use parameterized queries to prevent SQL injection.",
            metadata={"language": "python", "severity": "blocker"},
        )
        assert doc.doc_id == "TEST-001"
        assert doc.knowledge_type == KnowledgeType.BUG_PATTERN
        assert doc.embedding is None


class TestSearchQuery:
    def test_default_query(self):
        q = SearchQuery(query_text="SQL injection in login function")
        assert q.top_k == 5
        assert q.min_similarity == 0.7
        assert q.knowledge_types is None

    def test_filtered_query(self):
        q = SearchQuery(
            query_text="test",
            knowledge_types=[KnowledgeType.BUG_PATTERN],
            top_k=3,
            min_similarity=0.5,
        )
        assert q.top_k == 3
        assert len(q.knowledge_types) == 1


class TestRetrievalResult:
    def test_create_result(self):
        doc = KnowledgeDocument(
            doc_id="R-001",
            knowledge_type=KnowledgeType.BUG_PATTERN,
            title="Test", content="Test content",
        )
        result = RetrievalResult(document=doc, similarity_score=0.85)
        assert result.retrieval_method == "vector"
        assert 0.8 < result.similarity_score < 0.9


class TestKnowledgeType:
    def test_all_types(self):
        types = list(KnowledgeType)
        assert KnowledgeType.BUG_PATTERN in types
        assert KnowledgeType.CODING_STANDARD in types
        assert KnowledgeType.REVIEW_EXPERIENCE in types
