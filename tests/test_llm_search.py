import pytest
from app.embeddings import EmbeddingService
from app.vector_store import VectorStore
from app.llm import LLMService

def test_search_and_generate():
    embedder = EmbeddingService()
    vs = VectorStore()
    llm = LLMService()
    
    question = "What is used for backend processing?"
    
    # 1. Embed query
    query_emb = embedder.embed_text(question)
    assert len(query_emb) == 1536
    
    # 2. Search
    # This hits the live DB, results may be empty depending on ingestion state
    results = vs.search(query_emb, top_k=2)
    assert isinstance(results, list)
    
    # 3. Ask LLM (Synchronous)
    # We pass fake chunks to guarantee the LLM gets context regardless of Upstash state
    fake_chunks = [
        {"source": "test.md", "text": "We use FastAPI for backend processing."}
    ]
    
    answer = llm.generate_answer(question, fake_chunks)
    assert "FastAPI" in answer

    # 4. Ask LLM (Streaming)
    stream = llm.stream_answer(question, fake_chunks)
    full_text = ""
    for chunk in stream:
        full_text += chunk
    
    assert "FastAPI" in full_text
