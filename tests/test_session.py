import pytest
import uuid
from app.session import SessionStore

def test_session_handling():
    session_id = f"test_{uuid.uuid4().hex}"
    store = SessionStore()
    
    # 1. Initially Empty
    history = store.get_history(session_id)
    assert len(history) == 0
    
    # 2. Add Messages
    store.add_message(session_id, "user", "Hello there!")
    store.add_message(session_id, "assistant", "Hi! How can I help you?")
    store.add_message(session_id, "user", "What did I just say?")
    
    # 3. Retrieve
    history = store.get_history(session_id)
    assert len(history) == 3
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello there!"
    assert history[-1]["content"] == "What did I just say?"
    
    # 4. Limit behavior
    history_lim = store.get_history(session_id, limit=2)
    assert len(history_lim) == 2
    assert history_lim[0]["content"] == "Hi! How can I help you?"
