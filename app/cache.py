import hashlib
from typing import Optional, List
from upstash_redis import Redis
from app.config import settings
from app.vector_store import VectorStore

class SemanticCache:
    """Provides semantic caching capability utilizing Upstash Vector similarity and Upstash Redis metrics."""
    def __init__(self, vector_store: VectorStore):
        self.vs = vector_store
        # We use Upstash Redis for tracking cache hit metrics and storing cache IDs for flushing
        self.redis = Redis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token
        )
        self.threshold = 0.85  # Cosine similarity > 85% is considered a hit

    def check(self, query_emb: List[float]) -> Optional[str]:
        """Looks up the query embedding in the vector database to find semantically identical questions."""
        results = self.vs.index.query(
            vector=query_emb,
            top_k=5, # Fetch top 5 just to guarantee we bypass dense document regions
            include_metadata=True
        )
        
        for res in results:
            # We prefix cache IDs with 'cache::' so they are easily distinguishable from document chunks
            if str(res.id).startswith("cache::"):
                if res.score >= self.threshold:
                    self.redis.incr("rtfm:metrics:cache_hits")
                    return res.metadata["answer"]
                    
        self.redis.incr("rtfm:metrics:cache_misses")
        return None

    def put(self, query: str, query_emb: List[float], answer: str):
        """Saves a successful LLM answer into the vector database cache."""
        h = hashlib.sha256(query.encode()).hexdigest()
        vec_id = f"cache::{h}"
        
        self.vs.index.upsert(
            vectors=[(vec_id, query_emb, {"type": "cache", "answer": answer})]
        )
        # Keep track of the key so we can mass-delete the cache later if needed
        self.redis.sadd("rtfm:cache_keys", vec_id)

    def clear(self):
        """Flushes the semantic cache."""
        keys = self.redis.smembers("rtfm:cache_keys")
        if keys:
            self.vs.index.delete(keys)
            self.redis.delete("rtfm:cache_keys")

    def get_metrics(self) -> dict:
        """Retrieves hitting statistics."""
        hits = int(self.redis.get("rtfm:metrics:cache_hits") or 0)
        misses = int(self.redis.get("rtfm:metrics:cache_misses") or 0)
        total = hits + misses
        rate = (hits / total * 100) if total > 0 else 0
        return {"hits": hits, "misses": misses, "hit_rate": f"{rate:.1f}%"}
