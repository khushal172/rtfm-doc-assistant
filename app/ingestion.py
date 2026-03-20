from pathlib import Path
from typing import List, Dict, Any
from langchain_text_splitters import MarkdownTextSplitter

class DocumentLoader:
    """Loads documents from the filesystem."""
    @staticmethod
    def load_file(file_path: str | Path) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

class DocumentChunker:
    """Chunks documents into semantic blocks."""
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        # We use Langchain's MarkdownTextSplitter for paragraph/heading awareness
        self.splitter = MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def chunk_text(self, text: str, source: str) -> List[Dict[str, Any]]:
        """
        Chunks the text and attaches metadata.
        Returns a list of dicts: {"text": "...", "metadata": {"source": "...", "chunk_index": i}}
        """
        docs = self.splitter.create_documents([text])
        chunks = []
        for i, doc in enumerate(docs):
            chunks.append({
                "text": doc.page_content,
                "metadata": {
                    "source": source,
                    "chunk_index": i,
                    **doc.metadata
                }
            })
        return chunks
