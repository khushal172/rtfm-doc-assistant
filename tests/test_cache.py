import pytest
from app.embeddings import EmbeddingService
from app.vector_store import VectorStore
from app.cache import SemanticCache

def test_cache_hit_and_miss():
    embedder = EmbeddingService()
    vs = VectorStore()
    cache = SemanticCache(vs)
    
    # Reset tracking keys so we have a clean test
    cache.redis.delete("rtfm:metrics:cache_hits")
    cache.redis.delete("rtfm:metrics:cache_misses")
    
    question = "What is semantic caching?"
    query_emb = embedder.embed_text(question)
    
    # 1. It should MISS initially
    ans = cache.check(query_emb)
    assert ans is None
    
    # 2. We put it in the cache
    cache.put(question, query_emb, "It is a fast way to get repeated answers!")
    
    # Upstash indexing delay can take < 500ms, let's wait explicitly to avoid flaky testing
    import time
    time.sleep(1)
    
    # 3. It should HIT now
    ans2 = cache.check(query_emb)
    assert ans2 == "It is a fast way to get repeated answers!"
    
    # 4. Metrics should have exactly 1 miss and 1 hit
    metrics = cache.get_metrics()
    assert metrics["hits"] == 1
    assert metrics["misses"] == 1
    assert metrics["hit_rate"] == "50.0%"
    
    # 5. Flush and Verify
    cache.clear()
    time.sleep(1)
    ans3 = cache.check(query_emb)
    assert ans3 is None
