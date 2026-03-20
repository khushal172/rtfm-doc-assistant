import hashlib
from typing import List, Dict, Any
from upstash_vector import Index
from app.config import settings

class VectorStore:
    """Wrapper around Upstash Serverless Vector Database."""
    def __init__(self):
        self.index = Index(
            url=settings.upstash_vector_rest_url,
            token=settings.upstash_vector_rest_token
        )

    def _generate_id(self, source: str, chunk_index: int) -> str:
        """Deterministically generate an ID to handle re-ingestion deduplication."""
        s = f"{source}::{chunk_index}"
        return hashlib.sha256(s.encode()).hexdigest()

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Takes chunks and their corresponding embeddings and upserts them.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Mismatched chunks and embeddings lengths")
            
        if not chunks:
            return

        vectors = []
        for chunk, emb in zip(chunks, embeddings):
            vec_id = self._generate_id(
                source=chunk["metadata"]["source"], 
                chunk_index=chunk["metadata"]["chunk_index"]
            )
            
            # Combine text into metadata so we retrieve it upon search
            meta = chunk["metadata"].copy()
            meta["text"] = chunk["text"]
            
            vectors.append((vec_id, emb, meta))
            
        self.index.upsert(vectors=vectors)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Searches the vector store using KNN and returns the metadata (which contains the text)."""
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        # return list of metadata dicts
        return [res.metadata for res in results if res.metadata]
