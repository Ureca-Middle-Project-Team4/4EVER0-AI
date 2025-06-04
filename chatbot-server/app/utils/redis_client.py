import redis
import json

client = redis.Redis(host="localhost", port=6379, decode_responses=True)

def get_session(session_id: str) -> dict:
    data = client.get(session_id)
    return json.loads(data) if data else {}

def save_session(session_id: str, data: dict):
    try:
        client.set(session_id, json.dumps(data), ex=1800)  # 30분 TTL 적용 (만료 시간)
    except Exception as e:
        print(f"Redis 저장 실패: {e}")


def delete_session(session_id: str):
    client.delete(session_id)
