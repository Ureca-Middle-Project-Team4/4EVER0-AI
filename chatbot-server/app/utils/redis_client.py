import redis
import json
import os

redis_host = os.getenv("REDIS_HOST", "redis-ai")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

def get_session(session_id: str) -> dict:
    """세션 데이터 조회"""
    if not session_id:
        print("[ERROR] session_id is None or empty!")
        return {}

    try:
        data = client.get(session_id)
        session_data = json.loads(data) if data else {}
        print(f"[DEBUG] Redis get_session('{session_id}') → keys: {list(session_data.keys())}")
        return session_data
    except Exception as e:
        print(f"[ERROR] Redis get session failed: {e}")
        return {}


def save_session(session_id: str, data: dict):
    """세션 데이터 저장 - 🔥 멀티턴 키 보존"""
    try:
        # 멀티턴 관련 키들은 보존해야 함
        clean_data = data.copy()

        # 진짜로 불필요한 키들만 제거
        obsolete_keys = [
            "is_final_recommendation",
            "recommendation_type"
        ]
        
        for key in obsolete_keys:
            clean_data.pop(key, None)
        
        client.set(session_id, json.dumps(clean_data), ex=1800)  # 30분 TTL
        print(f"[DEBUG] Session saved with keys: {list(clean_data.keys())}")
    except Exception as e:
        print(f"[ERROR] Redis save session failed: {e}")

def delete_session(session_id: str):
    """세션 삭제"""
    try:
        client.delete(session_id)
        print(f"[DEBUG] Session deleted: {session_id}")
    except Exception as e:
        print(f"[ERROR] Redis delete session failed: {e}")

def clean_all_sessions():
    """모든 세션의 멀티턴 관련 키 정리 (관리자용)"""
    try:
        for key in client.scan_iter():
            session_data = get_session(key)
            if session_data:
                save_session(key, session_data)
        print(f"[DEBUG] All sessions cleaned")
    except Exception as e:
        print(f"[ERROR] Clean all sessions failed: {e}")