import json
from typing import List, Dict
from upstash_redis import Redis
from app.config import settings

class SessionStore:
    """Manages short-term conversation memory using Upstash Redis Lists."""
    def __init__(self):
        self.redis = Redis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token
        )
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
