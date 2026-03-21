from google import genai
from typing import List, Dict, Any, Generator
from app.config import settings

class LLMService:
    """Handles prompt assembly and interaction with Gemini 3.1 Flash Lite."""
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = "gemini-3.1-flash-lite-preview"

    def assemble_prompt(self, question: str, retrieved_chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None, memories: List[str] = None) -> str:
        """Constructs a RAG prompt using the provided document chunks, conversation history, and user memories."""
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
            
        memories_str = ""
        if memories:
            mem_lines = "\n".join([f"- {m}" for m in memories])
            memories_str = "LONG-TERM MEMORIES ABOUT USER:\n" + mem_lines + "\n\n"
        
        return f"""You are a professional documentation assistant. Use the following context and conversation history to answer the question.

### INSTRUCTIONS:
1.  **Format**: Use clear Markdown with headings and bullet points where appropriate.
2.  **Citations**: When you use information from a source, cite it in the text using bracketed numbers like [1], [2].
3.  **Sources Section**: ALWAYS end your response with a horizontal rule (`---`) followed by a "**Sources:**" section listing the filenames used.
4.  **Unknowns**: If the answer is not in the context, say "I don't know based on the provided documentation."

{memories_str}{history_str}CONTEXT:
{context}

QUESTION:
{question}
"""

    def generate_answer(self, question: str, retrieved_chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None, memories: List[str] = None) -> str:
        """Generates a fully formed answer string."""
        prompt = self.assemble_prompt(question, retrieved_chunks, history, memories)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text

    def stream_answer(self, question: str, retrieved_chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None, memories: List[str] = None) -> Generator[str, None, None]:
        """Streams the answer back in chunks."""
        prompt = self.assemble_prompt(question, retrieved_chunks, history, memories)
        response_stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    def summarize_code_batch(self, file_skeletons: Dict[str, str]) -> str:
        """
        Accepts a dictionary of `{filepath: skeleton}` and returns a JSON string
        of `{filepath: "purpose summary"}`. Batching this reduces RPM.
        """
        if not file_skeletons:
            return "{}"
            
        prompt = "You are an expert software architect. Analyze the provided file skeletons.\n"
        prompt += "For each file, determine its primary purpose in 1-2 sentences.\n"
        prompt += "Return the result STRICTLY as a valid JSON object where keys are the file paths and values are the summaries.\n\n"
        
        for fp, skel in file_skeletons.items():
            prompt += f"--- {fp} ---\n{skel}\n\n"
            
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            return response.text
        except Exception as e:
            from app.logging_config import logger
            logger.error(f"Failed to batch summarize: {e}")
            return "{}"
