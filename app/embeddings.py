from typing import List
import numpy as np
from google import genai
from google.genai import types
from app.config import settings

class EmbeddingService:
    """Wrapper around Gemini's embedding model using MRL and normalization."""
    def __init__(self, dimensionality: int = 1536):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = "gemini-embedding-2-preview"
        self.dimensionality = dimensionality
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of texts and normalizes them."""
        if not texts:
            return []
            
        result = self.client.models.embed_content(
            model=self.model_name,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=self.dimensionality)
        )
        
        normalized_embeddings = []
        for emb_obj in result.embeddings:
            # Apply L2 normalization to preserve cosine similarity search accuracy
            vec = np.array(emb_obj.values)
            normed_vec = vec / np.linalg.norm(vec)
            normalized_embeddings.append(normed_vec.tolist())
            
        return normalized_embeddings

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string."""
        return self.embed_texts([text])[0]
