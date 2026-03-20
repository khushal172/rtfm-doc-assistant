import hashlib
from datetime import datetime
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

    def _generate_id(self, source: str, chunk_index: int, version: str) -> str:
        """Deterministically generate an ID to handle re-ingestion deduplication per version."""
        s = f"{source}::{version}::{chunk_index}"
        return hashlib.sha256(s.encode()).hexdigest()

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]], version: str = "1.0.0"):
        """
        Takes chunks and their corresponding embeddings and upserts them.
        Includes versioning and timestamp metadata.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Mismatched chunks and embeddings lengths")
            
        if not chunks:
            return

        ingested_at = datetime.utcnow().isoformat() + "Z"
        vectors = []
        for chunk, emb in zip(chunks, embeddings):
            vec_id = self._generate_id(
                source=chunk["metadata"]["source"], 
                chunk_index=chunk["metadata"]["chunk_index"],
                version=version
            )
            
            # Combine text into metadata
            meta = chunk["metadata"].copy()
            meta["text"] = chunk["text"]
            meta["version"] = version
            meta["ingested_at"] = ingested_at
            
            vectors.append((vec_id, emb, meta))
            
        self.index.upsert(vectors=vectors)

    def search(self, query_embedding: List[float], top_k: int = 5, query_text: str = None, user_id: str = None) -> List[Dict[str, Any]]:
        """Searches the vector store using KNN and applies keyword boosting if text is provided. Supports user_id isolation."""
        fetch_k = top_k * 3 if query_text else top_k
        
        # Build filter if user_id is provided
        filter_str = f"user_id = '{user_id}'" if user_id else ""
        
        results = self.index.query(
            vector=query_embedding,
            top_k=fetch_k,
            include_metadata=True,
            filter=filter_str
        )
        
        metadata_list = [res.metadata for res in results if res.metadata and "text" in res.metadata]
        
        if query_text:
            # Simple keyword boosting (Simulated Hybrid Search)
            keywords = [k.lower() for k in query_text.split() if len(k) > 3]
            for meta in metadata_list:
                # Basic string match
                content = meta.get("text", "").lower()
                bump = sum(0.1 for k in keywords if k in content)
                meta["_boost_score"] = bump
                
            metadata_list = sorted(metadata_list, key=lambda x: x.get("_boost_score", 0), reverse=True)
            
        return metadata_list[:top_k]
