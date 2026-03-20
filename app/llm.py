from google import genai
from typing import List, Dict, Any, Generator
from app.config import settings

class LLMService:
    """Handles prompt assembly and interaction with Gemini 2.5 Flash."""
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = "gemini-2.5-flash"

    def assemble_prompt(self, question: str, retrieved_chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
        """Constructs a RAG prompt using the provided document chunks and conversation history."""
        context = "\n\n".join([
            f"--- Source: {chunk.get('source', 'Unknown')} ---\n{chunk.get('text', '')}" 
            for chunk in retrieved_chunks
        ])
        
        history_str = ""
        if history:
            history_lines = []
            for h in history:
                role = "User" if h["role"] == "user" else "Assistant"
                history_lines.append(f"{role}: {h['content']}")
            history_str = "PREVIOUS CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n\n"
        
        return f"""You are a helpful documentation assistant. Use the following context and conversation history to answer the user's question. 
If the answer is not in the context, say "I don't know based on the provided documentation."
Always cite your sources if you use them.

{history_str}CONTEXT:
{context}

QUESTION:
{question}
"""

    def generate_answer(self, question: str, retrieved_chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
        """Generates a fully formed answer string."""
        prompt = self.assemble_prompt(question, retrieved_chunks, history)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text

    def stream_answer(self, question: str, retrieved_chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> Generator[str, None, None]:
        """Streams the answer back in chunks."""
        prompt = self.assemble_prompt(question, retrieved_chunks, history)
        response_stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
