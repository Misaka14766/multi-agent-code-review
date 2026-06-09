"""RAG Engine — hybrid retrieval combining vector search with keyword matching."""

import logging
from .schemas import SearchQuery, RetrievalResult, KnowledgeDocument, KnowledgeType
from .embeddings import EmbeddingGenerator
from .vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

MIN_SIMILARITY_SPECULATIVE = 0.7


class RAGEngine:
    """Orchestrates knowledge retrieval: embedding → vector search → reranking."""

    def __init__(self, vector_store: ChromaVectorStore, embedding_gen: EmbeddingGenerator):
        self.vector_store = vector_store
        self.embedding_gen = embedding_gen

    async def retrieve(self, query: SearchQuery) -> list[RetrievalResult]:
        """Execute a complete retrieval pipeline for the given query."""
        query_embedding = await self.embedding_gen.embed(query.query_text)
        results = await self.vector_store.query(
            query_embedding=query_embedding,
            top_k=query.top_k,
            filter_types=query.knowledge_types,
        )
        # Filter by minimum similarity
        filtered = [r for r in results if r.similarity_score >= query.min_similarity]
        # Rerank: boost results that match keywords in the query text
        if filtered:
            filtered = self._rerank(query.query_text, filtered)
        return filtered[:query.top_k]

    async def index_documents(self, documents: list[KnowledgeDocument]) -> int:
        """Index a batch of knowledge documents into the vector store."""
        return await self.vector_store.add(documents, self.embedding_gen)

    async def search_similar_bugs(self, code_snippet: str, top_k: int = 5) -> list[RetrievalResult]:
        """Convenience: search for bug patterns similar to a code snippet."""
        query = SearchQuery(
            query_text=code_snippet,
            knowledge_types=[KnowledgeType.BUG_PATTERN],
            top_k=top_k,
            min_similarity=0.5,
        )
        return await self.retrieve(query)

    async def get_coding_standards(self, language: str = "python") -> list[RetrievalResult]:
        """Convenience: retrieve coding standards for a language."""
        query = SearchQuery(
            query_text=f"{language} coding standards best practices",
            knowledge_types=[KnowledgeType.CODING_STANDARD, KnowledgeType.ARCHITECTURE_RULE],
            top_k=5,
            min_similarity=0.5,
        )
        return await self.retrieve(query)

    @staticmethod
    def _rerank(query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Boost results whose content contains query keywords."""
        keywords = set(query.lower().split())
        for r in results:
            content_lower = r.document.content.lower()
            keyword_hits = sum(1 for kw in keywords if kw in content_lower)
            if keyword_hits > 0:
                r.similarity_score = min(1.0, r.similarity_score + 0.05 * keyword_hits)
                r.retrieval_method = "hybrid"
        return sorted(results, key=lambda r: r.similarity_score, reverse=True)

    def is_speculative(self, result: RetrievalResult) -> bool:
        """Check if a retrieval result is below the confidence threshold."""
        return result.similarity_score < MIN_SIMILARITY_SPECULATIVE
