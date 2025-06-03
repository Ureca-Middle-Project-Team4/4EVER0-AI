import redis
import json
import os

client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

def get_session(session_id: str) -> dict:
    data = client.get(session_id)
    return json.loads(data) if data else {}

def save_session(session_id: str, data: dict):
    client.set(session_id, json.dumps(data))
