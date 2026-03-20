from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ingestion import DocumentChunker
from app.embeddings import EmbeddingService
from app.vector_store import VectorStore
from app.llm import LLMService

app = FastAPI(title="RTFM Agent API", version="0.1.0")

# Initialize global services
chunker = DocumentChunker()
embedder = EmbeddingService()
vector_store = VectorStore()
llm = LLMService()

class ChatRequest(BaseModel):
    question: str

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
    """Retrieves relevant context and answers the user's question via streaming."""
    try:
        # 1. Embed Question
        query_emb = embedder.embed_text(request.question)
        
        # 2. Search
        retrieved_chunks = vector_store.search(query_emb, top_k=5)
        
        # 3. Generate Stream
        def event_stream():
            stream = llm.stream_answer(request.question, retrieved_chunks)
            for chunk_text in stream:
                yield chunk_text
                
        return StreamingResponse(event_stream(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
