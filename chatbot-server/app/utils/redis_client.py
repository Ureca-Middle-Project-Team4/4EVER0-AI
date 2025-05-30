import redis
import json
import os

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

def get_session(session_id: str) -> dict:
    data = r.get(session_id)
    return json.loads(data) if data else {}

# 1800초 = 30분동안 유지
def save_session(session_id: str, state: dict, ttl: int = 1800):
    r.setex(session_id, ttl, json.dumps(state))
