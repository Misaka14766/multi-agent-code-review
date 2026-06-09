"""Tests for seed knowledge data."""
from src.knowledge.seed_data import get_seed_documents
from src.knowledge.schemas import KnowledgeType


class TestSeedData:
    def test_has_documents(self):
        docs = get_seed_documents()
        assert len(docs) >= 8

    def test_all_have_ids(self):
        docs = get_seed_documents()
        ids = [d.doc_id for d in docs]
        assert len(ids) == len(set(ids)), "Duplicate doc_ids found"

    def test_has_bug_patterns(self):
        docs = get_seed_documents()
        bugs = [d for d in docs if d.knowledge_type == KnowledgeType.BUG_PATTERN]
        assert len(bugs) >= 3

    def test_has_coding_standards(self):
        docs = get_seed_documents()
        std = [d for d in docs if d.knowledge_type == KnowledgeType.CODING_STANDARD]
        assert len(std) >= 1

    def test_has_review_experience(self):
        docs = get_seed_documents()
        exp = [d for d in docs if d.knowledge_type == KnowledgeType.REVIEW_EXPERIENCE]
        assert len(exp) >= 1

    def test_all_have_content(self):
        docs = get_seed_documents()
        for d in docs:
            assert len(d.content) > 20, f"Document {d.doc_id} content too short"
            assert d.title
