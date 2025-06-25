import redis
import json
import os
from typing import Dict

# 환경 설정
redis_host = os.getenv("REDIS_HOST", "redis-ai")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
MEMORY_LIMIT_MB = int(os.getenv("REDIS_MEMORY_LIMIT_MB", "50"))
SESSION_TTL = int(os.getenv("SESSION_TTL", "600"))
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "500"))

print(f"[DEBUG] Redis 설정: {redis_host}:{redis_port} / TTL={SESSION_TTL}s")

def create_redis_client():
    """Redis 클라이언트 생성 - 실패 시 localhost로 fallback"""
    for host in [redis_host, "localhost"]:
        try:
            client = redis.Redis(
                host=host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            client.ping()  # 연결 확인

            # Redis 메모리 설정
            try:
                client.config_set('maxmemory', f'{MEMORY_LIMIT_MB}mb')
                client.config_set('maxmemory-policy', 'allkeys-lru')
                print(f"[INFO] Redis 메모리 정책 설정 완료: {MEMORY_LIMIT_MB}MB")
            except Exception as e:
                print(f"[WARNING] Redis 설정 실패: {e}")

            print(f"[SUCCESS] Redis 연결 성공: {host}:{redis_port}")
            return client
        except Exception as e:
            print(f"[ERROR] Redis 연결 실패 ({host}): {e}")
    return None


client = create_redis_client()

def clean_session_data(data: dict) -> dict:
    """불필요한 키 제거 + history 자르기"""
    essential_keys = {
        'phone_plan_flow_step', 'subscription_flow_step',
        'user_info', 'history',
        'plan_step', 'subscription_step',
        'plan_info', 'subscription_info',
        'ubti_step', 'ubti_info',
        'step', 'answers'
    }
    cleaned = {}
    for k, v in data.items():
        if k in essential_keys:
            if k == 'history' and isinstance(v, list):
                cleaned[k] = v[-10:]
            else:
                cleaned[k] = v
    return cleaned

def get_session(session_id: str) -> dict:
    if not session_id or not client:
        return {}
    try:
        raw = client.get(session_id)
        if not raw:
            return {}
        session_data = json.loads(raw)
        return clean_session_data(session_data)
    except Exception as e:
        print(f"[ERROR] 세션 조회 실패: {e}")
        return {}

def save_session(session_id: str, data: dict):
    if not client:
        return
    try:
        cleaned = clean_session_data(data)
        json_data = json.dumps(cleaned, ensure_ascii=False, separators=(',', ':'))

        ttl = SESSION_TTL // 2 if len(json_data) > 5120 else SESSION_TTL
        client.set(session_id, json_data, ex=ttl)

        if hash(session_id) % 10 == 0:
            cleanup_old_sessions()

        print(f"[DEBUG] 세션 저장: {session_id} ({len(json_data)} bytes, TTL={ttl}s)")
    except Exception as e:
        print(f"[ERROR] 세션 저장 실패: {e}")

def delete_session(session_id: str):
    if client:
        try:
            client.delete(session_id)
            print(f"[DEBUG] 세션 삭제: {session_id}")
        except Exception as e:
            print(f"[ERROR] 세션 삭제 실패: {e}")

def cleanup_old_sessions():
    if not client:
        return
    try:
        if client.dbsize() > MAX_SESSIONS:
            print(f"[WARNING] 세션 수 초과 → 정리 시작")
            keys_to_delete = []
            for key in client.scan_iter(count=100):
                if client.ttl(key) < 60 or len(keys_to_delete) >= 100:
                    keys_to_delete.append(key)
            if keys_to_delete:
                client.delete(*keys_to_delete)
                print(f"[DEBUG] {len(keys_to_delete)}개 세션 삭제 완료")
    except Exception as e:
        print(f"[ERROR] 세션 정리 실패: {e}")

def get_redis_memory_info():
    """Redis 메모리 사용량 정보"""
    if not client:
        return {"error": "Redis 연결 없음"}

    try:
        info = client.info('memory')
        return {
            "used_memory_human": info.get('used_memory_human'),
            "used_memory_peak_human": info.get('used_memory_peak_human'),
            "maxmemory_human": info.get('maxmemory_human', 'unlimited'),
            "total_keys": client.dbsize()
        }
    except Exception as e:
        return {"error": str(e)}

def emergency_cleanup():
    """긴급 메모리 정리 - 모든 세션 삭제"""
    if not client:
        return False

    try:
        client.flushdb()
        print("[WARNING] 긴급 메모리 정리 - 모든 세션 삭제됨")
        return True
    except Exception as e:
        print(f"[ERROR] 긴급 정리 실패: {e}")
        return False
