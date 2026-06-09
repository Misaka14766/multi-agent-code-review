"""Tests for embedding generator."""
import pytest
from src.knowledge.embeddings import EmbeddingGenerator, MOCK_EMBEDDING_DIM


class TestEmbeddingGenerator:
    @pytest.mark.asyncio
    async def test_mock_embed_returns_vector(self):
        gen = EmbeddingGenerator()  # No API key → mock mode
        assert not gen.is_available

        vec = await gen.embed("SELECT * FROM users WHERE name = 'admin'")
        assert len(vec) == MOCK_EMBEDDING_DIM
        assert all(-1.5 <= v <= 1.5 for v in vec)

    @pytest.mark.asyncio
    async def test_mock_embed_deterministic(self):
        gen = EmbeddingGenerator()
        v1 = await gen.embed("SQL injection in login function")
        v2 = await gen.embed("SQL injection in login function")
        assert v1 == v2

    @pytest.mark.asyncio
    async def test_mock_embed_different_texts_different(self):
        gen = EmbeddingGenerator()
        v1 = await gen.embed("SQL injection vulnerability")
        v2 = await gen.embed("Code style formatting issue")
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_embed_documents(self):
        from src.knowledge.schemas import KnowledgeDocument, KnowledgeType
        gen = EmbeddingGenerator()
        docs = [
            KnowledgeDocument(doc_id="D1", knowledge_type=KnowledgeType.BUG_PATTERN, title="T1", content="SQL injection"),
            KnowledgeDocument(doc_id="D2", knowledge_type=KnowledgeType.CODING_STANDARD, title="T2", content="PEP 8 style guide"),
        ]
        result = await gen.embed_documents(docs)
        assert len(result) == 2
        assert result[0].embedding is not None
        assert len(result[0].embedding) == MOCK_EMBEDDING_DIM  # type: ignore[arg-type]
