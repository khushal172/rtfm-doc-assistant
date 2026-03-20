import json
from typing import List, Dict
from upstash_redis import Redis
from google import genai
from app.config import settings

class SessionStore:
    """Manages short-term conversation memory using Upstash Redis Lists."""
    def __init__(self):
        self.redis = Redis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token
        )
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.ttl = 86400  # 24 hours

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Returns the last N messages of a session."""
        if not session_id:
            return []
            
        key = f"session:{session_id}"
        # Fetch the most recent N items
        raw_msgs = self.redis.lrange(key, -limit, -1)
        
        history = []
        for msg_str in raw_msgs:
            if msg_str:
                history.append(json.loads(msg_str))
        return history

    def add_message(self, session_id: str, role: str, content: str):
        """Appends a message to the session list and refreshes TTL."""
        if not session_id:
            return
            
        key = f"session:{session_id}"
        msg = json.dumps({"role": role, "content": content})
        self.redis.rpush(key, msg)
        self.redis.expire(key, self.ttl)
        
    def summarize_history(self, session_id: str):
        """Condenses lengthy conversation into a single summary block to save token context size."""
        key = f"session:{session_id}"
        raw_msgs = self.redis.lrange(key, 0, -1)
        if len(raw_msgs) <= 1:
            return
            
        history_text = "\n".join([f"{json.loads(m).get('role')}: {json.loads(m).get('content')}" for m in raw_msgs if m])
        try:
            resp = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Summarize the following chat history briefly so an AI agent can retain the context without losing specific facts:\n\n{history_text}"
            )
            summary = resp.text
            # Wipe list and push summary as first message
            self.redis.delete(key)
            self.redis.rpush(key, json.dumps({"role": "system", "content": f"Previous session summary: {summary}"}))
            self.redis.expire(key, self.ttl)
        except Exception as e:
            # Fallback to simple clipping
            self.redis.ltrim(key, -10, -1)
