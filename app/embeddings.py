from typing import List
import numpy as np
from fastembed import TextEmbedding
from app.logging_config import logger

class EmbeddingService:
    """Wrapper around local FastEmbed model to avoid Gemini API rate limits."""
    def __init__(self, dimensionality: int = 384):
        # We use bge-small-en-v1.5 which is very fast and has 384 dimensions
        logger.info("Initializing local FastEmbed TextEmbedding (BAAI/bge-small-en-v1.5)")
        self.client = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.dimensionality = dimensionality
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of texts locally and normalizes them."""
        if not texts:
            return []
            
        # FastEmbed returns a generator of embeddings
        embeddings_gen = self.client.embed(texts)
        
        normalized_embeddings = []
        for vec in embeddings_gen:
            # L2 normalization for cosine similarity
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            normalized_embeddings.append(vec.tolist())
            
        return normalized_embeddings

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string."""
        results = self.embed_texts([text])
        return results[0] if results else []
