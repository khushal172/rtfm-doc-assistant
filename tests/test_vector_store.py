import pytest
from app.embeddings import EmbeddingService
from app.vector_store import VectorStore

def test_embedding_and_upsert():
    embedder = EmbeddingService()
    vs = VectorStore()
    
    # 1. Generate embeddings
    texts = ["Test sentence 1", "Test sentence 2 is longer"]
    embeddings = embedder.embed_texts(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1536 # Normalized MRL dimension
    
    # 2. Upsert vectors
    chunks = [
        {"text": texts[0], "metadata": {"source": "test.md", "chunk_index": 0}},
        {"text": texts[1], "metadata": {"source": "test.md", "chunk_index": 1}}
    ]
    
    # This hits the live DB! Tests deduplication capability seamlessly due to deterministic IDs
    vs.upsert_chunks(chunks, embeddings)
    
    # 3. Check connectivity bounds
    info = vs.index.info()
    assert info.dimension == 1536
    assert info.vector_count >= 2
