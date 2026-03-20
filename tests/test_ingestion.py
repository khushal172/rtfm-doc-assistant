import pytest
from pathlib import Path
from app.ingestion import DocumentLoader, DocumentChunker

def test_load_and_chunk():
    sample_path = Path("docs/sample.md")
    
    # 1. Test Loading
    text = DocumentLoader.load_file(sample_path)
    assert "RTFM Agent" in text
    
    # 2. Test Chunking (keep chunk size small to force multiple chunks)
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk_text(text, source="sample.md")
    
    assert len(chunks) > 1
    assert chunks[0]["metadata"]["source"] == "sample.md"
    assert chunks[0]["metadata"]["chunk_index"] == 0
    assert "text" in chunks[0]
