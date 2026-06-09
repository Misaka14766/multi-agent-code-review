"""Chroma vector store wrapper for knowledge document storage and retrieval."""

import logging
from .schemas import KnowledgeDocument, RetrievalResult, KnowledgeType
from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """Persistent vector store backed by ChromaDB for knowledge retrieval."""

    def __init__(self, persist_dir: str = "./chroma_data", collection_name: str = "code_review_knowledge"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _ensure_collection(self):
        """Lazy-init ChromaDB client and collection."""
        if self._collection is not None:
            return
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection(name=self.collection_name)
            logger.info("ChromaDB initialized at %s (collection: %s)", self.persist_dir, self.collection_name)
        except ImportError:
            logger.warning("chromadb not installed. Run: pip install chromadb")
            raise
        except Exception as e:
            logger.warning("ChromaDB init failed: %s", e)
            raise

    def _is_available(self) -> bool:
        try:
            self._ensure_collection()
            return True
        except Exception:
            return False

    async def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_types: list[KnowledgeType] | None = None,
    ) -> list[RetrievalResult]:
        """Search for documents similar to the query embedding."""
        if not self._is_available():
            return []

        where_filter = None
        if filter_types:
            where_filter = {"knowledge_type": {"$in": [t.value for t in filter_types]}}

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning("Chroma query failed: %s", e)
            return []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        retrieval_results: list[RetrievalResult] = []
        for i, content in enumerate(documents):
            meta = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            similarity = max(0.0, min(1.0, 1.0 - distance))
            retrieval_results.append(RetrievalResult(
                document=KnowledgeDocument(
                    doc_id=meta.get("doc_id", f"result-{i}"),
                    knowledge_type=KnowledgeType(meta.get("knowledge_type", "bug_pattern")),
                    title=meta.get("title", ""),
                    content=content,
                    metadata=meta,
                ),
                similarity_score=similarity,
                retrieval_method="vector",
            ))
        return retrieval_results

    async def add(self, documents: list[KnowledgeDocument], embedding_gen: EmbeddingGenerator) -> int:
        """Index a batch of documents with their embeddings."""
        if not self._is_available():
            return 0

        docs_with_embeddings = await embedding_gen.embed_documents(documents)

        ids = []
        contents = []
        embeddings = []
        metadatas = []
        for doc in docs_with_embeddings:
            if doc.embedding is None:
                continue
            ids.append(doc.doc_id)
            contents.append(doc.content)
            embeddings.append(doc.embedding)
            metadatas.append({
                "doc_id": doc.doc_id,
                "knowledge_type": doc.knowledge_type.value,
                "title": doc.title,
                "source_issue_id": doc.source_issue_id or "",
                **doc.metadata,
            })

        if ids:
            try:
                self._collection.add(ids=ids, documents=contents, embeddings=embeddings, metadatas=metadatas)
                return len(ids)
            except Exception as e:
                logger.warning("Chroma add failed: %s", e)
        return 0

    async def delete(self, doc_ids: list[str]) -> int:
        """Remove documents by ID."""
        if not self._is_available():
            return 0
        try:
            self._collection.delete(ids=doc_ids)
            return len(doc_ids)
        except Exception:
            return 0
