from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ingestion import DocumentChunker
from app.embeddings import EmbeddingService
from app.vector_store import VectorStore
from app.llm import LLMService
from app.cache import SemanticCache

import json
from datetime import datetime
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

from fastapi import Header

@app.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    version: Optional[str] = None,
    user_id: str = Depends(verify_token),
    x_brain_id: str = Header("default")
):
    """Ingests a markdown or text file, chunks it, embeds it, and saves to Upstash."""
    if not file.filename:
        logger.warning(f"Ingest call rejected for user {user_id}: No file provided")
        raise HTTPException(status_code=400, detail="No file provided")
        
    doc_version = version or datetime.utcnow().strftime("%Y%m%d-%H%M")
    
    try:
        content = await file.read()
        text = content.decode("utf-8")
        
        logger.info(f"User {user_id} ingesting file: {file.filename} (v{doc_version})")
        chunks = chunker.chunk_text(text, source=file.filename)
        
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = embedder.embed_texts(texts_to_embed)
        
        vector_store.upsert_chunks(chunks, embeddings, version=doc_version, brain_id=x_brain_id, user_id=user_id)
        
        # Track document metadata in Redis for easy listing (segmented by brain)
        doc_key = f"user:{user_id}:brain:{x_brain_id}:documents"
        doc_info = {
            "filename": file.filename,
            "version": doc_version,
            "ingested_at": datetime.utcnow().isoformat() + "Z"
        }
        # We store as a JSON string in a HASH where key is the filename
        # This allows easy "latest version" tracking
        session_store.redis.hset(doc_key, file.filename, json.dumps(doc_info))
        
        logger.info(f"Successfully ingested {len(chunks)} chunks for user {user_id} (v{doc_version}).")
        return {
            "message": "Document ingested successfully", 
            "chunks": len(chunks), 
            "source": file.filename,
            "version": doc_version
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_token),
    x_brain_id: str = Header("default")
):
    """Retrieves relevant context and answers the user's question via streaming. Isolated by user_id."""
    try:
        logger.info(f"User {user_id} processing chat request for session: '{request.session_id}' in brain: {x_brain_id}")
        # Ensure session ID is globally unique by prefixing user_id and brain_id
        actual_session_id = f"{user_id}:{x_brain_id}:{request.session_id}" if request.session_id else f"{user_id}:{x_brain_id}:default"
        
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
            
        # 3. Fetch Long Term Memories for this user and brain
        memories = []
        try:
            memories = ltm.retrieve_memories(query_emb, user_id, brain_id=x_brain_id)
        except Exception as e:
            logger.warning(f"Long term memory retrieval failed: {e}. Degrading gracefully.")
        
        # 4. Hybrid Search Document Chunks (Isolated by user_id and brain_id)
        retrieved_chunks = vector_store.search(query_emb, top_k=5, query_text=request.question, user_id=user_id, brain_id=x_brain_id)
        
        # 4.5 Staleness Detection
        # Check if any retrieved chunks are older than the latest version in Redis
        stale_docs = []
        try:
            doc_key = f"user:{user_id}:brain:{x_brain_id}:documents"
            registry = session_store.redis.hgetall(doc_key)
            
            for chunk in retrieved_chunks:
                source = chunk.get("source")
                chunk_ver = chunk.get("version")
                if source in registry:
                    latest_info = json.loads(registry[source])
                    latest_ver = latest_info.get("version")
                    if chunk_ver != latest_ver and source not in [d["source"] for d in stale_docs]:
                        stale_docs.append({"source": source, "using": chunk_ver, "latest": latest_ver})
        except Exception as e:
            logger.warning(f"Staleness detection failed: {e}")

        # 5. Generate Stream
        def event_stream():
            full_answer = []
            
            # If we found stale docs, prepend a warning to the stream (or add to prompt)
            if stale_docs:
                warning = f"⚠️ *Note: Some information is from older versions ({', '.join([f'{d['source']} v{d['using']}' for d in stale_docs])}). Newer versions are available.* \n\n"
                yield warning
                full_answer.append(warning)

            stream = llm.stream_answer(request.question, retrieved_chunks, history, memories)
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
                        # Tie memory to user_id and brain_id
                        ltm.save_memory(user_id, fact, brain_id=x_brain_id)
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

@app.get("/documents")
async def list_documents(user_id: str = Depends(verify_token), x_brain_id: str = Header("default")):
    """Returns a list of all ingested documents and their current versions for the user and brain."""
    try:
        doc_key = f"user:{user_id}:brain:{x_brain_id}:documents"
        docs = session_store.redis.hgetall(doc_key)
        
        result = []
        for filename, data_str in docs.items():
            result.append(json.loads(data_str))
            
        return sorted(result, key=lambda x: x["ingested_at"], reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{filename}")
async def delete_document(filename: str, user_id: str = Depends(verify_token), x_brain_id: str = Header("default")):
    """Deletes a document and all its chunks from the vector store and registry for a specific brain."""
    try:
        # 1. Purge from Vector Store
        count = vector_store.delete_chunks(filename, user_id, brain_id=x_brain_id)
        
        # 2. Remove from Redis Registry
        doc_key = f"user:{user_id}:brain:{x_brain_id}:documents"
        session_store.redis.hdel(doc_key, filename)
        
        logger.info(f"User {user_id} deleted document '{filename}' from brain '{x_brain_id}' ({count} chunks removed).")
        return {"message": f"Document '{filename}' deleted successfully", "chunks_removed": count}
    except Exception as e:
        logger.error(f"Deletion failed for document '{filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/brains")
async def list_brains(user_id: str = Depends(verify_token)):
    """Returns all knowledge spaces (brains) for the user."""
    brains_key = f"user:{user_id}:brains"
    brains = session_store.redis.smembers(brains_key)
    if not brains:
        # Create default brain if first time
        session_store.redis.sadd(brains_key, "default")
        return ["default"]
    return list(brains)

@app.post("/brains/{brain_id}")
async def create_brain(brain_id: str, user_id: str = Depends(verify_token)):
    """Creates a new knowledge space."""
    brains_key = f"user:{user_id}:brains"
    session_store.redis.sadd(brains_key, brain_id)
    return {"message": f"Brain '{brain_id}' created"}

@app.delete("/brains/{brain_id}")
async def delete_brain(brain_id: str, user_id: str = Depends(verify_token)):
    """Deletes a brain (Registry only, vectors stay but become unreachable)."""
    if brain_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default brain")
    brains_key = f"user:{user_id}:brains"
    session_store.redis.srem(brains_key, brain_id)
    return {"message": f"Brain '{brain_id}' removed from registry"}

@app.get("/debug-index")
async def debug_index(user_id: Optional[str] = None):
    """Broad diagnostic endpoint to inspect raw vector metadata."""
    try:
        dummy_emb = [0.0] * 1536
        filter_str = f"user_id = '{user_id}'" if user_id else ""
        
        logger.info(f"DEBUG INDEX CALL: user_id={user_id}, filter='{filter_str}'")
        
        results = vector_store.index.query(
            vector=dummy_emb,
            top_k=50,
            include_metadata=True,
            filter=filter_str if filter_str else None
        )
        
        return {
            "requested_user_id": user_id,
            "count": len(results),
            "results": [
                {
                    "id": r.id,
                    "metadata": r.metadata
                } for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Debug index failed: {e}")
        return {"error": str(e)}

@app.delete("/cache")
async def clear_cache():
    """Flushes the semantic cache index."""
    try:
        semantic_cache.clear()
        return {"message": "Semantic cache flushed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
