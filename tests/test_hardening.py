import pytest
from app.vector_store import VectorStore
from app.embeddings import EmbeddingService

def test_hybrid_search():
    vs = VectorStore()
    embedder = EmbeddingService()
    
    question = "How to run the API via python?"
    query_emb = embedder.embed_text(question)
    
    # We test the keyword booster
    res = vs.search(query_emb, top_k=5, query_text="python")
    assert isinstance(res, list)

def test_graceful_degradation(mocker):
    from fastapi.testclient import TestClient
    from app.main import app
    
    # Mock SemanticCache.check to throw an exception
    mocker.patch("app.cache.SemanticCache.check", side_effect=Exception("Cache crashed completely"))
    
    client = TestClient(app)
    
    # The API should gracefully catch it, bypass it, and still return 200 OK because of the LLM fallback!
    res = client.post("/chat", json={"question": "Test graceful fail?"})
    assert res.status_code == 200
