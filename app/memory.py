import hashlib
from typing import List, Optional
from google import genai
from app.config import settings
from app.vector_store import VectorStore
from app.embeddings import EmbeddingService

class LongTermMemory:
    """Extracts and stores salient facts about the user across sessions."""
    def __init__(self, vector_store: VectorStore, embedder: EmbeddingService):
        self.vs = vector_store
        self.embedder = embedder
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = "gemini-2.5-flash"

    def extract_fact(self, user_msg: str, agent_response: str) -> Optional[str]:
        """Uses a quick LLM call to extract any long-term preferences or facts about the user."""
        prompt = f"""You are a personal memory extraction assistant. 
Review the following exchange and extract any permanent facts, preferences, or contextual information about the user that should be remembered for future conversations.
If there are no new personal facts or preferences, respond exactly with "NONE".

USER MESSAGE: {user_msg}
AGENT RESPONSE: {agent_response}

Extracted Fact (or NONE):"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            fact = response.text.strip().replace('"', "")
            if fact == "NONE" or not fact:
                return None
            return fact
        except Exception:
            return None

    def save_memory(self, user_id: str, fact: str):
        """Embeds and saves the extracted fact to the vector index, tied to a user_id."""
        if not fact: return
        
        emb = self.embedder.embed_text(fact)
        h = hashlib.sha256(fact.encode()).hexdigest()
        vec_id = f"memory::{user_id}::{h}"
        
        self.vs.index.upsert(
            vectors=[(vec_id, emb, {"type": "memory", "fact": fact, "user_id": user_id})]
        )

    def retrieve_memories(self, query_emb: List[float], user_id: str, top_k: int = 3) -> List[str]:
        """Finds relevant past facts conceptually related to the current query, filtered by user_id."""
        results = self.vs.index.query(
            vector=query_emb,
            top_k=top_k + 5, # Overfetch to bypass other chunk types
            include_metadata=True,
            filter=f"user_id = '{user_id}'"
        )
        memories = []
        for res in results:
            if str(res.id).startswith("memory::"):
                if res.score > 0.70: # lower threshold for general associative recall
                    memories.append(res.metadata["fact"])
                    
        return memories[:top_k]
