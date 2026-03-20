from google import genai
from typing import List, Dict, Any, Generator
from app.config import settings

class LLMService:
    """Handles prompt assembly and interaction with Gemini 2.5 Flash."""
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = "gemini-2.5-flash"

    def assemble_prompt(self, question: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Constructs a RAG prompt using the provided document chunks."""
        context = "\n\n".join([
            f"--- Source: {chunk.get('source', 'Unknown')} ---\n{chunk.get('text', '')}" 
            for chunk in retrieved_chunks
        ])
        
        return f"""You are a helpful documentation assistant. Use the following context to answer the user's question. 
If the answer is not in the context, say "I don't know based on the provided documentation."
Always cite your sources if you use them.

CONTEXT:
{context}

QUESTION:
{question}
"""

    def generate_answer(self, question: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Generates a fully formed answer string."""
        prompt = self.assemble_prompt(question, retrieved_chunks)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text

    def stream_answer(self, question: str, retrieved_chunks: List[Dict[str, Any]]) -> Generator[str, None, None]:
        """Streams the answer back in chunks."""
        prompt = self.assemble_prompt(question, retrieved_chunks)
        response_stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
