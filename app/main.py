from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ingestion import DocumentChunker
from app.embeddings import EmbeddingService
from app.vector_store import VectorStore
from app.llm import LLMService
from app.cache import SemanticCache

from typing import Optional
from app.session import SessionStore

app = FastAPI(title="RTFM Agent API", version="0.1.0")

# Initialize global services
chunker = DocumentChunker()
embedder = EmbeddingService()
vector_store = VectorStore()
llm = LLMService()
semantic_cache = SemanticCache(vector_store)
session_store = SessionStore()

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Ingests a markdown or text file, chunks it, embeds it, and saves to Upstash."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    try:
        content = await file.read()
        text = content.decode("utf-8")
        
        # 1. Chunking
        chunks = chunker.chunk_text(text, source=file.filename)
        
        # 2. Embedding
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = embedder.embed_texts(texts_to_embed)
        
        # 3. Upsert to Vector Store
        vector_store.upsert_chunks(chunks, embeddings)
        
        return {
            "message": "Document ingested successfully", 
            "chunks": len(chunks), 
            "source": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """Retrieves relevant context and answers the user's question via streaming. Implements Semantic Caching & Memory."""
    try:
        # 1. Embed Question
        query_emb = embedder.embed_text(request.question)
        
        # 2. Check Cache
        cached_answer = semantic_cache.check(query_emb)
        if cached_answer:
            if request.session_id:
                session_store.add_message(request.session_id, "user", request.question)
                session_store.add_message(request.session_id, "assistant", cached_answer)
                
            async def cache_stream():
                yield cached_answer
            return StreamingResponse(cache_stream(), media_type="text/plain")
        
        # 3. Fetch Session History
        history = session_store.get_history(request.session_id) if request.session_id else []
        
        # 4. Search Document Chunks
        retrieved_chunks = vector_store.search(query_emb, top_k=5)
        
        # 5. Generate Stream and intercept
        def event_stream():
            full_answer = []
            stream = llm.stream_answer(request.question, retrieved_chunks, history)
            for chunk_text in stream:
                full_answer.append(chunk_text)
                yield chunk_text
            
            final_ans = "".join(full_answer)
            semantic_cache.put(request.question, query_emb, final_ans)
            
            if request.session_id:
                session_store.add_message(request.session_id, "user", request.question)
                session_store.add_message(request.session_id, "assistant", final_ans)
                
        return StreamingResponse(event_stream(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """Returns caching hit rates and LLM deflection metrics."""
    try:
        return semantic_cache.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/cache")
async def clear_cache():
    """Flushes the semantic cache index."""
    try:
        semantic_cache.clear()
        return {"message": "Semantic cache flushed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
