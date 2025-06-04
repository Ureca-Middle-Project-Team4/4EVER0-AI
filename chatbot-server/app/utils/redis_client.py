# app/utils/redis_client.py
import redis
import json

client = redis.Redis(host="localhost", port=6379, decode_responses=True)

def get_session(session_id: str) -> dict:
    data = client.get(session_id)
    return json.loads(data) if data else {}

def save_session(session_id: str, data: dict):
    client.set(session_id, json.dumps(data))

def delete_session(session_id: str):
    client.delete(session_id)
