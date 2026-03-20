import hashlib
from datetime import datetime
from typing import List, Dict, Any
from upstash_vector import Index
from app.config import settings

import logging
logger = logging.getLogger("uvicorn.error")

class VectorStore:
    """Wrapper around Upstash Serverless Vector Database."""
    def __init__(self):
        self.index = Index(
            url=settings.upstash_vector_rest_url,
            token=settings.upstash_vector_rest_token
        )

    def _generate_id(self, source: str, chunk_index: int, version: str, brain_id: str = "default", user_id: str = "unknown") -> str:
        """Deterministically generate an ID to handle re-ingestion deduplication per user, version and brain."""
        s = f"{user_id}::{brain_id}::{source}::{version}::{chunk_index}"
        return hashlib.sha256(s.encode()).hexdigest()

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]], version: str = "1.0.0", brain_id: str = "default", user_id: str = "unknown"):
        """
        Takes chunks and their corresponding embeddings and upserts them.
        Includes versioning, brain isolation, user isolation, and timestamp metadata.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Mismatched chunks and embeddings lengths")
            
        if not chunks:
            return

        ingested_at = datetime.utcnow().isoformat() + "Z"
        # Ensure we have strings for isolation
        u_id = user_id or "anonymous"
        b_id = brain_id or "default"

        vectors = []
        for chunk, emb in zip(chunks, embeddings):
            vec_id = self._generate_id(
                source=chunk["metadata"]["source"], 
                chunk_index=chunk["metadata"]["chunk_index"],
                version=version,
                brain_id=b_id,
                user_id=u_id
            )
            with open("ingest_trace.txt", "a") as f:
                f.write(f"{datetime.utcnow().isoformat()} - GENERATED ID: {vec_id}\n")
            
            # Combine text into metadata
            meta = chunk["metadata"].copy()
            meta["text"] = chunk["text"]
            meta["version"] = version
            meta["brain_id"] = b_id
            meta["user_id"] = u_id
            meta["ingested_at"] = ingested_at
            
            vectors.append((vec_id, emb, meta))
            
        logger.info(f"SUCCESS: Upserting {len(vectors)} vectors | user='{u_id}' | brain='{b_id}' | meta_keys={list(vectors[0][2].keys())}")
        res = self.index.upsert(vectors=vectors)

    def search(self, query_embedding: List[float], top_k: int = 5, query_text: str = None, user_id: str = None, brain_id: str = "default") -> List[Dict[str, Any]]:
        """Searches the vector store using KNN and applies keyword boosting. Supports user_id and brain_id isolation."""
        fetch_k = top_k * 3 if query_text else top_k
        
        # Build filter for user_id and brain_id
        u_id = user_id or "anonymous"
        b_id = brain_id or "default"
        filters = [f"user_id = '{u_id}'", f"brain_id = '{b_id}'"]
        
        filter_str = " AND ".join(filters)
        logger.info(f"Vector search: filter='{filter_str}', top_k={fetch_k}")
        
        results = self.index.query(
            vector=query_embedding,
            top_k=fetch_k,
            include_metadata=True,
            filter=filter_str
        )
        logger.info(f"Vector search returned {len(results)} results")
        for i, res in enumerate(results[:3]):
            logger.debug(f"Result {i}: id={res.id}, score={res.score}, meta_keys={list(res.metadata.keys()) if res.metadata else 'None'}")
        
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

    def delete_chunks(self, filename: str, user_id: str, brain_id: str = "default"):
        """
        Deletes all chunks associated with a specific file, user, and brain.
        Query for IDs first, then delete.
        """
        # Query for all IDs matching the metadata
        dummy_emb = [0.0] * 1536
        res = self.index.query(
            vector=dummy_emb,
            top_k=1000, 
            include_metadata=False,
            filter=f"source = '{filename}' AND user_id = '{user_id}' AND brain_id = '{brain_id}'"
        )
        
        ids_to_delete = [r.id for r in res]
        if ids_to_delete:
            self.index.delete(ids=ids_to_delete)
            return len(ids_to_delete)
        return 0
