from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings

class EmbeddingService:
    """Wrapper around Gemini's text-embedding-004 model via LangChain."""
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-2-preview",
            google_api_key=settings.gemini_api_key
        )
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of texts."""
        if not texts:
            return []
            
        return self.embeddings.embed_documents(texts)

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string."""
        return self.embeddings.embed_query(text)
