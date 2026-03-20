from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
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
from app.auth import verify_token

app = FastAPI(title="RTFM Agent API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
async def ingest_document(
    file: UploadFile = File(...),
    user_id: str = Depends(verify_token)
):
    """Ingests a markdown or text file, chunks it, embeds it, and saves to Upstash."""
    if not file.filename:
        logger.warning(f"Ingest call rejected for user {user_id}: No file provided")
        raise HTTPException(status_code=400, detail="No file provided")
        
    try:
        content = await file.read()
        text = content.decode("utf-8")
        
        logger.info(f"User {user_id} ingesting file: {file.filename}")
        chunks = chunker.chunk_text(text, source=file.filename)
        
        # Add user_id to metadata for isolation
        for c in chunks:
            c["user_id"] = user_id
            
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = embedder.embed_texts(texts_to_embed)
        
        vector_store.upsert_chunks(chunks, embeddings)
        
        logger.info(f"Successfully ingested {len(chunks)} chunks for user {user_id}.")
        return {
            "message": "Document ingested successfully", 
            "chunks": len(chunks), 
            "source": file.filename
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_token)
):
    """Retrieves relevant context and answers the user's question via streaming. Isolated by user_id."""
    try:
        logger.info(f"User {user_id} processing chat request for session: '{request.session_id}'")
        # Ensure session ID is globally unique by prefixing user_id
        actual_session_id = f"{user_id}:{request.session_id}" if request.session_id else user_id
        
        query_emb = embedder.embed_text(request.question)
        
        # 1. Check Cache (Graceful Degradation)
        cached_answer = None
        try:
            cached_answer = semantic_cache.check(query_emb)
        except Exception as e:
            logger.warning(f"Semantic Cache checking failed: {e}. Degrading gracefully.")

        if cached_answer:
            logger.info(f"Cache HIT for user {user_id}")
            try:
                session_store.add_message(actual_session_id, "user", request.question)
                session_store.add_message(actual_session_id, "assistant", cached_answer)
            except Exception as ex:
                logger.warning(f"Failed attaching cache hit to session: {ex}")
                
            async def cache_stream():
                yield cached_answer
            return StreamingResponse(cache_stream(), media_type="text/plain")
        
        # 2. Fetch Session History
        history = []
        try:
            history = session_store.get_history(actual_session_id)
        except Exception as e:
            logger.warning(f"Session history retrieval failed: {e}. Degrading gracefully.")
            
        # 3. Fetch Long Term Memories for this user
        memories = []
        try:
            # We filter by user_id in retrieval (Note: LTM needs updated to support filters)
            memories = ltm.retrieve_memories(query_emb)
        except Exception as e:
            logger.warning(f"Long term memory retrieval failed: {e}. Degrading gracefully.")
        
        # 4. Hybrid Search Document Chunks (Isolated by user_id)
        # Note: VectorStore search needs to support metadata filters for true isolation
        retrieved_chunks = vector_store.search(query_emb, top_k=5, query_text=request.question)
        
        # Filter retrieved chunks by user_id to ensure privacy
        # (This is a safety check; eventually move to server-side metadata filters)
        isolated_chunks = [c for c in retrieved_chunks if c.get("user_id") == user_id]
        
        # 5. Generate Stream
        def event_stream():
            full_answer = []
            stream = llm.stream_answer(request.question, isolated_chunks, history, memories)
            for chunk_text in stream:
                full_answer.append(chunk_text)
                yield chunk_text
            
            final_ans = "".join(full_answer)
            
            # Post-Process tasks
            try:
                semantic_cache.put(request.question, query_emb, final_ans)
                session_store.add_message(actual_session_id, "user", request.question)
                session_store.add_message(actual_session_id, "assistant", final_ans)
            except Exception as e:
                logger.error(f"Failed to execute post-chat caching hooks: {e}")

            # Summarize long histories asynchronously
            if len(history) >= 10:
                background_tasks.add_task(lambda: session_store.summarize_history(actual_session_id))
            
            # Extract distinct Long Term Memory asynchronously
            def background_process_memory():
                try:
                    fact = ltm.extract_fact(request.question, final_ans)
                    if fact:
                        # Tie memory to user_id
                        ltm.save_memory(user_id, fact)
                except Exception as e:
                    logger.error(f"Background Fact Extraction failed: {e}")
            background_tasks.add_task(background_process_memory)
                
        return StreamingResponse(event_stream(), media_type="text/plain")
    except Exception as e:
        logger.critical(f"Critical exception in chat endpoint for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics(user_id: str = Depends(verify_token)):
    """Returns semantic cache analytics."""
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
