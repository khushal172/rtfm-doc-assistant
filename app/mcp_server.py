import logging
from mcp.server.fastmcp import FastMCP
from typing import List, Optional

from app.embeddings import EmbeddingService
from app.vector_store import VectorStore
from app.llm import LLMService
from app.memory import LongTermMemory
from app.session import SessionStore

# Initialize MCP Server
mcp = FastMCP("RTFM Agent")

# Initialize Backend Services
embedder = EmbeddingService()
vector_store = VectorStore()
llm = LLMService()
ltm = LongTermMemory(vector_store, embedder)
session_store = SessionStore()

@mcp.tool()
def ask_rtfm(question: str, user_id: str = "mcp-user") -> str:
    """
    Ask any question to the RTFM Documentation Agent.
    It will retrieve relevant context from ingested documents and answer.
    """
    try:
        query_emb = embedder.embed_text(question)
        
        # 1. Retrieve Memories
        memories = ltm.retrieve_memories(query_emb, user_id)
        
        # 2. Search Docs
        chunks = vector_store.search(query_emb, top_k=5, query_text=question, user_id=user_id)
        
        # 3. Generate Answer (No history for tool calls unless stateful)
        stream = llm.stream_answer(question, chunks, history=[], memories=memories)
        
        full_answer = "".join([chunk for chunk in stream])
        
        # 4. Optional: Save query to session (using user_id as session)
        session_store.add_message(user_id, "user", question)
        session_store.add_message(user_id, "assistant", full_answer)
        
        return full_answer
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def search_docs(query: str, user_id: str = "mcp-user", limit: int = 5) -> str:
    """
    Search through the ingested documentation chunks using hybrid search.
    Returns the most relevant text snippets.
    """
    try:
        query_emb = embedder.embed_text(query)
        chunks = vector_store.search(query_emb, top_k=limit, query_text=query, user_id=user_id)
        
        if not chunks:
            return "No relevant documentation found."
            
        formatted = []
        for i, c in enumerate(chunks):
            formatted.append(f"[{i+1}] Source: {c.get('source')} (v{c.get('version')})\nContent: {c.get('text')}\n")
            
        return "\n---\n".join(formatted)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def list_memories(user_id: str = "mcp-user") -> str:
    """
    Retrieve all long-term facts and memories stored for this user.
    """
    try:
        # We perform a broad search for memory types
        # Since we don't have a 'list all' for vectors easily, we use a wide dummy search
        dummy_emb = [0.0] * 1536
        memories = ltm.retrieve_memories(dummy_emb, user_id, top_k=20)
        
        if not memories:
            return "No stored memories found for this user."
            
        return "\n".join([f"• {m}" for m in memories])
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # When run directly, this starts the stdio server
    mcp.run()
