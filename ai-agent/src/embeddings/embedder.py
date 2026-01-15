"""
Embedder - Generates embeddings for text using OpenAI
"""

from typing import List, Optional
import structlog
from openai import AsyncOpenAI

from src.config import settings

logger = structlog.get_logger()


class Embedder:
    """
    Generates text embeddings using OpenAI's embedding models.
    """

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        self.client = client
        self.model = settings.embedding_model
        self._cache = {}  # Simple in-memory cache

    async def initialize(self):
        """Initialize the embedder"""
        if not self.client and settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)

        logger.info(f"Embedder initialized with model: {self.model}")

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding
        """
        if not text:
            return [0.0] * 1536  # Return zero vector for empty text

        # Check cache
        cache_key = hash(text[:1000])  # Use first 1000 chars for cache key
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text[:8000],  # Limit input size
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            # Cache result
            self._cache[cache_key] = embedding

            # Limit cache size
            if len(self._cache) > 10000:
                # Remove oldest entries
                keys = list(self._cache.keys())[:5000]
                for k in keys:
                    del self._cache[k]

            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * 1536

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        if not texts:
            return []

        # Filter out empty texts and track indices
        non_empty = [(i, t) for i, t in enumerate(texts) if t]

        if not non_empty:
            return [[0.0] * 1536 for _ in texts]

        try:
            # Process in batches of 100
            batch_size = 100
            all_embeddings = {}

            for batch_start in range(0, len(non_empty), batch_size):
                batch = non_empty[batch_start:batch_start + batch_size]
                batch_texts = [t[:8000] for _, t in batch]

                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch_texts,
                    encoding_format="float"
                )

                for (original_idx, _), embedding_data in zip(batch, response.data):
                    all_embeddings[original_idx] = embedding_data.embedding

            # Build result list maintaining original order
            result = []
            for i in range(len(texts)):
                if i in all_embeddings:
                    result.append(all_embeddings[i])
                else:
                    result.append([0.0] * 1536)

            return result

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return [[0.0] * 1536 for _ in texts]

    async def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score (0-1)
        """
        if not embedding1 or not embedding2:
            return 0.0

        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Calculate magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
