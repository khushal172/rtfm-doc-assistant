import asyncio
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
from app.github_service import GithubService
from app.github_processor import GithubProcessor

app = FastAPI(title="RTFM Agent API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://rtfm-doc-assistant.vercel.app"
    ],
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
github_processor = GithubProcessor()
session_store = SessionStore()
ltm = LongTermMemory(vector_store, embedder)

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

from fastapi import Header

@app.get("/test-headers")
async def test_headers(x_brain_id: Optional[str] = Header(None)):
    return {"X-Brain-Id": x_brain_id}

@app.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    version: Optional[str] = None,
    user_id: str = Depends(verify_token),
    x_brain_id: str = Header("default")
):
    logger.info(f"INGEST: user={user_id}, brain={x_brain_id}, file={file.filename}")
    if not file.filename:
        logger.warning(f"Ingest call rejected for user {user_id}: No file provided")
        raise HTTPException(status_code=400, detail="No file provided")
        
    doc_version = version or datetime.utcnow().strftime("%Y%m%d-%H%M")
    
    try:
        content = await file.read()
        text = content.decode("utf-8")
        with open("ingest_trace.txt", "a") as f:
            f.write(f"{datetime.utcnow().isoformat()} - CONTENT READ: {len(text)} chars\n")
        
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
        
        # Invalidate semantic cache for this brain
        semantic_cache.clear(user_id=user_id, brain_id=x_brain_id)
        
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

@app.post("/ingest-github")
async def ingest_github(
    url: str,
    background_tasks: BackgroundTasks,
    brain_id: Optional[str] = None,
    user_id: str = Depends(verify_token),
    x_brain_id: str = Header("default"),
    github_token: Optional[str] = Header(None)
):
    """Triggers background ingestion of a public GitHub repository."""
    gh = GithubService(token=github_token)
    actual_brain_id = brain_id or x_brain_id
    try:
        repo_info = gh.parse_github_url(url)
        logger.info(f"GitHub Ingest Triggered: {repo_info['owner']}/{repo_info['repo']} for user {user_id} into brain {actual_brain_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid GitHub URL: {str(e)}")

    async def background_ingest():
        import io
        import zipfile
        import asyncio
        
        try:
            # 1. Download full ZIP (Single request to GitHub)
            logger.info(f"Downloading ZIP for {repo_info['owner']}/{repo_info['repo']}...")
            zip_data = await gh.download_repo_zip(**repo_info)
            
            chunk_buffer = []
            file_registry_buffer = set() 
            
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                all_files = z.namelist()
                # Filter files
                files_to_index = [f for f in all_files if gh.should_index(f)]
                logger.info(f"Found {len(files_to_index)} valid files in ZIP. Starting indexing...")

                # Track progress in Redis
                progress_key = f"rtfm:ingest:{user_id}:progress"
                progress_data = {
                    "repo": f"{repo_info['owner']}/{repo_info['repo']}",
                    "total_files": len(files_to_index),
                    "processed_files": 0,
                    "status": "indexing",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                await asyncio.to_thread(session_store.redis.set, progress_key, json.dumps(progress_data))

                for i, file_path in enumerate(files_to_index):
                    try:
                        with z.open(file_path) as f:
                            content = f.read().decode("utf-8", errors="replace")
                            
                        # Clean path (GitHub zip often prefixes with owner-repo-hash/)
                        display_path = "/".join(file_path.split("/")[1:]) if "/" in file_path else file_path
                        if not display_path: continue # Skip root dir
                        
                        # 1. AST Extraction
                        skeleton = github_processor.extract_skeleton(content, display_path)
                        
                        chunk_buffer.append({
                            "display_path": display_path,
                            "skeleton": skeleton,
                            "content": content
                        })
                        
                        # IF buffer has 20 files or it's the last file, flush it
                        if len(chunk_buffer) >= 20 or i == len(files_to_index) - 1:
                            while chunk_buffer:
                                batch = chunk_buffer[:20] 
                                chunk_buffer = chunk_buffer[20:]
                                
                                logger.info(f"Summarizing and Embedding batch of {len(batch)} files...")
                                try:
                                    # 2. Batch Summarize with LLM
                                    skeletons_dict = {item["display_path"]: item["skeleton"] for item in batch}
                                    summaries_json = await asyncio.to_thread(llm.summarize_code_batch, skeletons_dict)
                                    try:
                                        summaries = json.loads(summaries_json)
                                    except Exception:
                                        summaries = {}
                                        
                                    vector_chunks = []
                                    texts_to_embed = []
                                    
                                    for item in batch:
                                        path = item["display_path"]
                                        summary = summaries.get(path, "No summary available.")
                                        combined_text = f"File: {path}\nSummary: {summary}\n\nSkeleton:\n{item['skeleton']}"
                                        
                                        vector_chunks.append({
                                            "text": combined_text,
                                            "metadata": {"source": path, "chunk_index": 0}
                                        })
                                        texts_to_embed.append(combined_text)
                                        
                                        # 3. Save Full Text to Redis
                                        redis_key = f"rtfm:repo:{user_id}:{actual_brain_id}:{path}:content"
                                        await asyncio.to_thread(session_store.redis.set, redis_key, item["content"])
                                        file_registry_buffer.add(path)
                                        
                                    # 4. Embed (locally) and Upsert
                                    embeddings = await asyncio.to_thread(embedder.embed_texts, texts_to_embed)
                                    await asyncio.to_thread(
                                        vector_store.upsert_chunks,
                                        vector_chunks, 
                                        embeddings, 
                                        version=f"github-{repo_info['branch']}", 
                                        brain_id=actual_brain_id, 
                                        user_id=user_id
                                    )
                                except Exception as embed_err:
                                    logger.error(f"Batch processing failed: {embed_err}")
                                    await asyncio.sleep(1) # Brief pause on error
                                    
                            # Update registry for files processed so far
                            doc_key = f"user:{user_id}:brain:{actual_brain_id}:documents"
                            for f_path in file_registry_buffer:
                                doc_info = {
                                    "filename": f_path,
                                    "version": f_path,
                                    "ingested_at": datetime.utcnow().isoformat() + "Z"
                                }
                                await asyncio.to_thread(session_store.redis.hset, doc_key, f_path, json.dumps(doc_info))
                            file_registry_buffer.clear()

                    except Exception as file_err:
                        logger.warning(f"Failed to process file {file_path}: {file_err}")
                        
                    # Update Redis progress for EVERY file processed, even if it failed
                    progress_data["processed_files"] = i + 1
                    progress_data["timestamp"] = datetime.utcnow().isoformat() + "Z"
                    if i == len(files_to_index) - 1:
                        progress_data["status"] = "completed"
                    await asyncio.to_thread(session_store.redis.set, progress_key, json.dumps(progress_data))
                    await asyncio.to_thread(session_store.redis.expire, progress_key, 600)
            
            # Invalidate semantic cache for this brain
            semantic_cache.clear(user_id=user_id, brain_id=actual_brain_id)
            logger.info(f"GitHub Ingest Complete for {repo_info['owner']}/{repo_info['repo']}.")
        except Exception as e:
            logger.error(f"Background GitHub Ingest failed: {e}", exc_info=True)
            # Report failure to Redis so UI can stop polling
            progress_key = f"rtfm:ingest:{user_id}:progress"
            error_data = {
                "repo": f"{repo_info['owner']}/{repo_info['repo']}",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            try:
                await asyncio.to_thread(session_store.redis.set, progress_key, json.dumps(error_data))
                await asyncio.to_thread(session_store.redis.expire, progress_key, 300) # Keep error for 5 mins
            except Exception as redis_err:
                logger.error(f"Failed to write error status to Redis: {redis_err}")

    # Proactively clear/reset progress state so the UI doesn't see old 100% data
    progress_key = f"rtfm:ingest:{user_id}:progress"
    logger.info(f"Resetting ingest progress for user {user_id} (key: {progress_key})")
    await asyncio.to_thread(session_store.redis.delete, progress_key)

    background_tasks.add_task(background_ingest)
    return {"message": "GitHub ingestion started in background", "repo": f"{repo_info['owner']}/{repo_info['repo']}"}

@app.get("/ingest-status")
async def get_ingest_status(
    user_id: str = Depends(verify_token)
):
    """Retrieves the current ingestion progress for a user."""
    progress_key = f"rtfm:ingest:{user_id}:progress"
    data = session_store.redis.get(progress_key)
    if not data:
        return {"status": "idle"}
    
    status_data = json.loads(data)
    logger.info(f"Status check for {user_id}: {status_data.get('status')} ({status_data.get('processed_files')}/{status_data.get('total_files')})")
    return status_data

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
            cached_answer = semantic_cache.check(query_emb, user_id=user_id, brain_id=x_brain_id)
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
        
        # 4.2 Expand Skeletons to Full Text (Long-Context Retrieval)
        for chunk in retrieved_chunks:
            source = chunk.get("source")
            if source:
                redis_key = f"rtfm:repo:{user_id}:{x_brain_id}:{source}:content"
                try:
                    full_text = session_store.redis.get(redis_key)
                    if full_text:
                        if isinstance(full_text, bytes):
                            full_text = full_text.decode("utf-8", errors="replace")
                        chunk["text"] = f"File: {source}\n\n{full_text}"
                except Exception as e:
                    logger.warning(f"Failed to retrieve full text from Redis for {source}: {e}")
        
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
                warning = "> ⚠️ **Stale Data Warning**\n"
                warning += "> Some information may be out of date. Documents being used:\n"
                for d in stale_docs:
                    warning += f"> - **{d['source']}**: using v{d['using'].split('-')[-1] if '-' in d['using'] else d['using']} (latest: v{d['latest'].split('-')[-1] if '-' in d['latest'] else d['latest']})\n"
                warning += "\n"
                yield warning
                full_answer.append(warning)

            stream = llm.stream_answer(request.question, retrieved_chunks, history, memories)
            for chunk_text in stream:
                full_answer.append(chunk_text)
                yield chunk_text
            
            final_ans = "".join(full_answer)
            
            # Post-Process tasks
            try:
                semantic_cache.put(request.question, query_emb, final_ans, user_id=user_id, brain_id=x_brain_id)
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

@app.delete("/documents/{filename:path}")
async def delete_document(filename: str, user_id: str = Depends(verify_token), x_brain_id: str = Header("default")):
    """Deletes a document and all its chunks from the vector store and registry for a specific brain."""
    try:
        # 1. Purge from Vector Store
        count = vector_store.delete_chunks(filename, user_id, brain_id=x_brain_id)
        
        # 2. Remove from Redis Registry
        doc_key = f"user:{user_id}:brain:{x_brain_id}:documents"
        session_store.redis.hdel(doc_key, filename)
        
        # Invalidate semantic cache for this brain
        semantic_cache.clear(user_id=user_id, brain_id=x_brain_id)
        
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
async def debug_index(passcode: str = None):
    """Global diagnostic endpoint (unauthenticated for debugging)."""
    if passcode != "antigravity":
        return {"error": "Invalid passcode. Use ?passcode=antigravity"}
        
    try:
        # Fetch index info and first 100 vectors
        info = vector_store.index.info()
        results = vector_store.index.range(
            cursor="0", 
            limit=100,
            include_metadata=True,
            include_vectors=False
        )
        return {
            "index_info": {
                "vector_count": info.vector_count,
                "pending_vector_count": info.pending_vector_count,
                "index_size": info.index_size,
                "dimension": info.dimension,
                "similarity_function": info.similarity_function
            },
            "count": len(results.vectors),
            "vectors": [
                {
                    "id": v.id,
                    "metadata": v.metadata
                } for v in results.vectors
            ]
        }
    except Exception as e:
        return {"error": str(e)}

@app.delete("/cache")
async def clear_cache(user_id: str = Depends(verify_token), x_brain_id: str = Header("default")):
    """Flushes the semantic cache index for the active brain."""
    try:
        semantic_cache.clear(user_id, x_brain_id)
        return {"message": "Semantic cache flushed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
