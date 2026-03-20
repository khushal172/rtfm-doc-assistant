from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ingestion import DocumentChunker
from app.embeddings import EmbeddingService
from app.vector_store import VectorStore
from app.llm import LLMService
from app.cache import SemanticCache

from typing import Optional
from app.session import SessionStore
from app.memory import LongTermMemory
from app.logging_config import logger

app = FastAPI(title="RTFM Agent API", version="0.1.0")

# Initialize global services
chunker = DocumentChunker()
embedder = EmbeddingService()
vector_store = VectorStore()
llm = LLMService()
semantic_cache = SemanticCache(vector_store)
session_store = SessionStore()
ltm = LongTermMemory(vector_store, embedder)

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Ingests a markdown or text file, chunks it, embeds it, and saves to Upstash."""
    if not file.filename:
        logger.warning("Ingest call rejected: No file provided")
        raise HTTPException(status_code=400, detail="No file provided")
        
    try:
        content = await file.read()
        text = content.decode("utf-8")
        
        logger.info(f"Ingesting file: {file.filename} with size: {len(text)} bytes")
        chunks = chunker.chunk_text(text, source=file.filename)
        
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = embedder.embed_texts(texts_to_embed)
        
        vector_store.upsert_chunks(chunks, embeddings)
        
        logger.info(f"Successfully ingested {len(chunks)} chunks into vector store.")
        return {
            "message": "Document ingested successfully", 
            "chunks": len(chunks), 
            "source": file.filename
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """Retrieves relevant context and answers the user's question via streaming. Includes gracefully degrading components."""
    try:
        logger.info(f"Processing chat request for session: '{request.session_id}'")
        query_emb = embedder.embed_text(request.question)
        
        # 1. Check Cache (Graceful Degradation)
        cached_answer = None
        try:
            cached_answer = semantic_cache.check(query_emb)
        except Exception as e:
            logger.warning(f"Semantic Cache checking failed: {e}. Degrading gracefully.")

        if cached_answer:
            logger.info("Semantic cache HIT! Intercepting request.")
            if request.session_id:
                try:
                    session_store.add_message(request.session_id, "user", request.question)
                    session_store.add_message(request.session_id, "assistant", cached_answer)
                except Exception as ex:
                    logger.warning(f"Failed attaching cache hit to session: {ex}")
                
            async def cache_stream():
                yield cached_answer
            return StreamingResponse(cache_stream(), media_type="text/plain")
        
        # 2. Fetch Session History (Graceful Degradation)
        history = []
        try:
            history = session_store.get_history(request.session_id) if request.session_id else []
        except Exception as e:
            logger.warning(f"Session history retrieval failed: {e}. Degrading gracefully.")
            
        # 3. Fetch Long Term Memories (Graceful Degradation)
        memories = []
        try:
            memories = ltm.retrieve_memories(query_emb)
        except Exception as e:
            logger.warning(f"Long term memory retrieval failed: {e}. Degrading gracefully.")
        
        # 4. Hybrid Search Document Chunks
        retrieved_chunks = vector_store.search(query_emb, top_k=5, query_text=request.question)
        
        # 5. Generate Stream
        def event_stream():
            full_answer = []
            stream = llm.stream_answer(request.question, retrieved_chunks, history, memories)
            for chunk_text in stream:
                full_answer.append(chunk_text)
                yield chunk_text
            
            final_ans = "".join(full_answer)
            logger.info("LLM generation complete. Dispatching background workers.")
            
            # Post-Process tasks
            try:
                semantic_cache.put(request.question, query_emb, final_ans)
                if request.session_id:
                    session_store.add_message(request.session_id, "user", request.question)
                    session_store.add_message(request.session_id, "assistant", final_ans)
            except Exception as e:
                logger.error(f"Failed to execute post-chat caching hooks: {e}")

            # Summarize long histories asynchronously
            if request.session_id and len(history) >= 10:
                background_tasks.add_task(lambda: session_store.summarize_history(request.session_id))
            
            # Extract distinct Long Term Memory asynchronously
            def background_process_memory():
                try:
                    fact = ltm.extract_fact(request.question, final_ans)
                    if fact:
                        ltm.save_memory(request.session_id or "anonymous", fact)
                except Exception as e:
                    logger.error(f"Background Fact Extraction failed: {e}")
            background_tasks.add_task(background_process_memory)
                
        return StreamingResponse(event_stream(), media_type="text/plain")
    except Exception as e:
        logger.critical(f"Critical exception in chat endpoint: {e}", exc_info=True)
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
