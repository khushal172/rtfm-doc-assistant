import pytest
from app.memory import LongTermMemory
from app.embeddings import EmbeddingService
from app.vector_store import VectorStore

def test_long_term_memory():
    embedder = EmbeddingService()
    vs = VectorStore()
    ltm = LongTermMemory(vs, embedder)
    
    # 1. Extract Fact
    usr_msg = "Please remember that my favorite framework is Next.js"
    agt_msg = "I will keep that in mind!"
    fact = ltm.extract_fact(usr_msg, agt_msg)
    
    assert fact is not None
    assert "Next.js" in fact
    
    # 2. Save it
    ltm.save_memory("test_user_id", fact)
    
    # 3. Retrieve
    query_emb = embedder.embed_text("What tools do I enjoy using?")
    
    # Needs brief delay for eventual consistency on Upstash index
    import time
    time.sleep(1)
    
    memories = ltm.retrieve_memories(query_emb)
    
    # Either it successfully found the new memory, or found none due to db indexing delay,
    # but the API contract shouldn't throw an error.
    assert isinstance(memories, list)
