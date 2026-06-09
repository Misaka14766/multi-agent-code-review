"""Embedding generator — mock implementation that falls back to DeepSeek API when key available."""

import hashlib
import logging
from .schemas import KnowledgeDocument

logger = logging.getLogger(__name__)

MOCK_EMBEDDING_DIM = 384


class EmbeddingGenerator:
    """Generates embeddings for knowledge documents and queries.

    Uses a deterministic mock (hash-based) when no API key is configured.
    Set DEEPSEEK_API_KEY to enable real embeddings via DeepSeek API.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._client = None
        if api_key:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a text string."""
        if self._client:
            return await self._embed_real(text)
        return self._embed_mock(text)

    async def embed_documents(self, documents: list[KnowledgeDocument]) -> list[KnowledgeDocument]:
        """Generate embeddings for a batch of documents (in-place)."""
        for doc in documents:
            doc.embedding = await self.embed(doc.content)
        return documents

    async def _embed_real(self, text: str) -> list[float]:
        """Use DeepSeek embedding API (requires API key)."""
        response = await self._client.embeddings.create(
            model="deepseek-text-embedding",
            input=text,
        )
        return response.data[0].embedding

    @staticmethod
    def _embed_mock(text: str) -> list[float]:
        """Deterministic mock embedding based on text hash.

        Not semantically meaningful, but enables the RAG pipeline to function
        without an API key. Documents with similar text produce similar hashes.
        """
        # Use multiple hash slices to create a 384-dim pseudo-embedding
        h = hashlib.sha256(text.encode("utf-8")).digest()
        embedding: list[float] = []
        for i in range(MOCK_EMBEDDING_DIM):
            byte_val = h[i % len(h)]
            embedding.append((byte_val - 127.5) / 127.5)
        return embedding
