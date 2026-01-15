"""
Vector Store - Manages vector embeddings for semantic search
"""

from typing import Any, Dict, List, Optional
import structlog

from src.config import settings

logger = structlog.get_logger()


class VectorStore:
    """
    Vector store for semantic search using Pinecone.
    Falls back to in-memory storage for development.
    """

    def __init__(self):
        self.pinecone_client = None
        self.index = None
        self._in_memory_store: Dict[str, List[Dict]] = {}
        self._use_pinecone = bool(settings.pinecone_api_key)

    async def initialize(self):
        """Initialize the vector store"""
        if self._use_pinecone:
            try:
                from pinecone import Pinecone

                self.pinecone_client = Pinecone(api_key=settings.pinecone_api_key)
                self.index = self.pinecone_client.Index(settings.pinecone_index)

                logger.info("Pinecone vector store initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Pinecone, using in-memory: {e}")
                self._use_pinecone = False

        if not self._use_pinecone:
            logger.info("Using in-memory vector store")

    async def close(self):
        """Close vector store connections"""
        pass  # Pinecone doesn't need explicit closing

    async def upsert(
        self,
        namespace: str,
        vectors: List[Dict[str, Any]]
    ) -> bool:
        """
        Upsert vectors into the store.

        Args:
            namespace: Namespace/partition for the vectors
            vectors: List of dicts with 'id', 'values', and optional 'metadata'

        Returns:
            Success boolean
        """
        if not vectors:
            return True

        try:
            if self._use_pinecone:
                # Format for Pinecone
                formatted = [
                    {
                        "id": v["id"],
                        "values": v["values"],
                        "metadata": v.get("metadata", {})
                    }
                    for v in vectors
                ]

                self.index.upsert(
                    vectors=formatted,
                    namespace=namespace
                )
            else:
                # In-memory storage
                if namespace not in self._in_memory_store:
                    self._in_memory_store[namespace] = []

                # Update or append
                existing_ids = {v["id"] for v in self._in_memory_store[namespace]}

                for vector in vectors:
                    if vector["id"] in existing_ids:
                        # Update existing
                        for i, v in enumerate(self._in_memory_store[namespace]):
                            if v["id"] == vector["id"]:
                                self._in_memory_store[namespace][i] = vector
                                break
                    else:
                        # Append new
                        self._in_memory_store[namespace].append(vector)

            logger.debug(f"Upserted {len(vectors)} vectors to {namespace}")
            return True

        except Exception as e:
            logger.error(f"Vector upsert failed: {e}")
            return False

    async def search(
        self,
        namespace: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            namespace: Namespace to search in
            query_embedding: Query vector
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of matching results with scores
        """
        if not query_embedding:
            return []

        try:
            if self._use_pinecone:
                results = self.index.query(
                    namespace=namespace,
                    vector=query_embedding,
                    top_k=top_k,
                    filter=filter,
                    include_metadata=True
                )

                return [
                    {
                        "id": match.id,
                        "score": match.score,
                        **match.metadata
                    }
                    for match in results.matches
                ]
            else:
                # In-memory cosine similarity search
                vectors = self._in_memory_store.get(namespace, [])

                if not vectors:
                    return []

                # Calculate similarities
                scored = []
                for vector in vectors:
                    score = self._cosine_similarity(
                        query_embedding,
                        vector.get("values", [])
                    )

                    # Apply filter if provided
                    if filter:
                        metadata = vector.get("metadata", {})
                        if not self._matches_filter(metadata, filter):
                            continue

                    scored.append({
                        "id": vector["id"],
                        "score": score,
                        **vector.get("metadata", {})
                    })

                # Sort by score and return top_k
                scored.sort(key=lambda x: x["score"], reverse=True)
                return scored[:top_k]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def delete(
        self,
        namespace: str,
        ids: Optional[List[str]] = None,
        delete_all: bool = False
    ) -> bool:
        """
        Delete vectors from the store.

        Args:
            namespace: Namespace to delete from
            ids: Specific IDs to delete
            delete_all: Delete all vectors in namespace

        Returns:
            Success boolean
        """
        try:
            if self._use_pinecone:
                if delete_all:
                    self.index.delete(
                        namespace=namespace,
                        delete_all=True
                    )
                elif ids:
                    self.index.delete(
                        namespace=namespace,
                        ids=ids
                    )
            else:
                if delete_all:
                    self._in_memory_store[namespace] = []
                elif ids:
                    self._in_memory_store[namespace] = [
                        v for v in self._in_memory_store.get(namespace, [])
                        if v["id"] not in ids
                    ]

            return True

        except Exception as e:
            logger.error(f"Vector delete failed: {e}")
            return False

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _matches_filter(self, metadata: Dict, filter: Dict) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter.items():
            if key not in metadata:
                return False

            if isinstance(value, dict):
                # Handle operators like $eq, $in, etc.
                for op, op_value in value.items():
                    if op == "$eq" and metadata[key] != op_value:
                        return False
                    elif op == "$in" and metadata[key] not in op_value:
                        return False
                    elif op == "$ne" and metadata[key] == op_value:
                        return False
            else:
                if metadata[key] != value:
                    return False

        return True
