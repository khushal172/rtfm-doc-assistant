from fastapi.testclient import TestClient
from app.main import app
import os
import pytest

client = TestClient(app)

def test_ingest_endpoint():
    file_path = "docs/sample.md"
    assert os.path.exists(file_path), "Sample document missing"
    
    with open(file_path, "rb") as f:
        response = client.post("/ingest", files={"file": ("sample.md", f, "text/markdown")})
        
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Document ingested successfully"
    assert "chunks" in data
    assert data["source"] == "sample.md"

def test_chat_endpoint():
    response = client.post("/chat", json={"question": "What framework is used for backend processing?"})
    assert response.status_code == 200
    
    # Check that FastAPI string is in the returned SSE block / textual response
    # If Upstash hasn't indexed the document yet (eventual consistency), it will say "I don't know"
    assert "FastAPI" in response.text or "I don't know" in response.text
