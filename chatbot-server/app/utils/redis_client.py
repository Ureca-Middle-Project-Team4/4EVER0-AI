import redis
import json
import os
from typing import Dict

# 안전한 최적화 설정 (기존 로직 유지)
redis_host = os.getenv("REDIS_HOST", "redis-ai")
redis_port = int(os.getenv("REDIS_PORT", "6379"))

# 현실적 최적화 (멀티턴 체인 보장)
MEMORY_LIMIT_MB = int(os.getenv("REDIS_MEMORY_LIMIT_MB", "20"))  # 50→20MB
SESSION_TTL = int(os.getenv("SESSION_TTL", "300"))  # 600→300초 (5분)
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "80"))  # 500→80개

print(f"[INFO] Redis 최적화: 메모리={MEMORY_LIMIT_MB}MB / TTL={SESSION_TTL}s / 최대={MAX_SESSIONS}개")

def create_redis_client():
    """Redis 클라이언트 - 기존 로직 호환"""
    for host in [redis_host, "localhost"]:
        try:
            client = redis.Redis(
                host=host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                max_connections=15,  # 연결 제한 추가
            )
            client.ping()

            # 메모리 최적화 설정만 적용
            try:
                client.config_set('maxmemory', f'{MEMORY_LIMIT_MB}mb')
                client.config_set('maxmemory-policy', 'allkeys-lru')
                # 영속성 비활성화 (메모리 절약)
                client.config_set('save', '')
                client.config_set('appendonly', 'no')
                print(f"[SUCCESS] Redis 메모리 최적화: {MEMORY_LIMIT_MB}MB")
            except Exception as e:
                print(f"[WARNING] Redis 설정 실패: {e}")

            return client
        except Exception as e:
            print(f"[ERROR] Redis 연결 실패 ({host}): {e}")
    return None

client = create_redis_client()

def safe_clean_session_data(data: dict) -> dict:
    """안전한 세션 정리 - 멀티턴 데이터 보존"""

    # 기존 로직 완전 보존하면서 최적화만 적용
    essential_keys = {
        # 기존 멀티턴 키들 모두 보존
        'phone_plan_flow_step', 'subscription_flow_step', 'ubti_step',
        'plan_step', 'subscription_step',  # 기존 키 호환성
        'user_info', 'plan_info', 'subscription_info', 'ubti_info',
        'history', 'last_recommendation_type',
        'step', 'answers'  # UBTI용
    }

    cleaned = {}
    for k, v in data.items():
        if k in essential_keys:
            if k == 'history' and isinstance(v, list):
                # 히스토리만 제한 (기존 10개 → 6개)
                cleaned[k] = v[-6:] if len(v) > 6 else v
            elif k in ['user_info', 'plan_info', 'subscription_info', 'ubti_info'] and isinstance(v, dict):
                # 사용자 정보는 길이만 제한
                compressed_info = {}
                for uk, uv in v.items():
                    if uv:
                        # 긴 텍스트만 자르기 (100자 초과시)
                        if isinstance(uv, str) and len(uv) > 100:
                            compressed_info[uk] = uv[:100]
                        else:
                            compressed_info[uk] = uv
                cleaned[k] = compressed_info
            else:
                # 나머지는 그대로 유지
                cleaned[k] = v

    return cleaned

def get_session(session_id: str) -> dict:
    """기존 함수 그대로 유지"""
    if not session_id or not client:
        return {}
    try:
        raw = client.get(session_id)
        if not raw:
            return {}
        session_data = json.loads(raw)
        return safe_clean_session_data(session_data)
    except Exception as e:
        print(f"[ERROR] 세션 조회 실패: {e}")
        return {}

def save_session(session_id: str, data: dict):
    """기존 로직 유지하면서 크기만 최적화"""
    if not client:
        return
    try:
        cleaned = safe_clean_session_data(data)
        json_data = json.dumps(cleaned, ensure_ascii=False, separators=(',', ':'))

        # 크기 모니터링 (경고만, 강제 삭제 안함)
        size_kb = len(json_data) / 1024

        if size_kb > 10.0:
            print(f"[WARNING] 세션 크기 과대 ({size_kb:.1f}KB) - {session_id}")
            # 강제 삭제 대신 히스토리만 더 줄임
            if 'history' in cleaned and isinstance(cleaned['history'], list):
                cleaned['history'] = cleaned['history'][-3:]  # 3개만 유지
                json_data = json.dumps(cleaned, ensure_ascii=False, separators=(',', ':'))
                size_kb = len(json_data) / 1024
                print(f"[INFO] 히스토리 압축 후: {size_kb:.1f}KB")

        # 동적 TTL
        if size_kb > 3.0:
            ttl = SESSION_TTL // 2  # 큰 세션은 짧은 TTL
        else:
            ttl = SESSION_TTL

        client.set(session_id, json_data, ex=ttl)

        # 주기적 정리 (덜 빈번하게)
        if hash(session_id) % 15 == 0:  # 15번에 1번
            cleanup_old_sessions()

        print(f"[DEBUG] 세션 저장: {session_id} ({size_kb:.1f}KB, TTL={ttl}s)")

    except Exception as e:
        print(f"[ERROR] 세션 저장 실패: {e}")

def cleanup_old_sessions():
    """안전한 세션 정리 - 만료된 것만"""
    if not client:
        return
    try:
        total_sessions = client.dbsize()

        # 세션이 60개 초과시 정리
        if total_sessions > 60:
            print(f"[INFO] 세션 정리 시작 (현재: {total_sessions}개)")

            keys_to_delete = []
            for key in client.scan_iter(count=30):
                ttl = client.ttl(key)
                # TTL이 30초 미만이거나 이미 만료된 키만 삭제
                if ttl < 30 or ttl == -1:
                    keys_to_delete.append(key)
                    if len(keys_to_delete) >= 15:  # 한 번에 15개까지
                        break

            if keys_to_delete:
                client.delete(*keys_to_delete)
                print(f"[INFO] 만료된 세션 정리: {len(keys_to_delete)}개")

    except Exception as e:
        print(f"[ERROR] 세션 정리 실패: {e}")

def delete_session(session_id: str):
    """기존 함수 그대로"""
    if client:
        try:
            client.delete(session_id)
            print(f"[DEBUG] 세션 삭제: {session_id}")
        except Exception as e:
            print(f"[ERROR] 세션 삭제 실패: {e}")

def get_redis_memory_info():
    """Redis 메모리 정보"""
    if not client:
        return {"error": "Redis 연결 없음"}

    try:
        info = client.info('memory')
        used_mb = info.get('used_memory', 0) / (1024 * 1024)

        return {
            "used_memory_human": info.get('used_memory_human'),
            "used_memory_mb": f"{used_mb:.1f}MB",
            "maxmemory_human": f"{MEMORY_LIMIT_MB}MB",
            "usage_percent": f"{(used_mb/MEMORY_LIMIT_MB)*100:.1f}%",
            "total_keys": client.dbsize(),
            "status": "healthy" if used_mb < MEMORY_LIMIT_MB * 0.8 else "warning"
        }
    except Exception as e:
        return {"error": str(e)}

def get_user_capacity_info():
    """현재 상태 기반 사용자 수용 능력 계산"""
    redis_info = get_redis_memory_info()

    if redis_info.get("error"):
        return {"error": "Redis 연결 실패"}

    # 현재 사용량 파싱
    used_mb = float(redis_info.get("used_memory_mb", "0").replace("MB", ""))
    total_sessions = redis_info.get("total_keys", 0)

    # 1세션당 평균 메모리 계산
    if total_sessions > 0:
        avg_memory_per_session = used_mb / total_sessions
    else:
        avg_memory_per_session = 0.5  # 기본값

    # 수용 가능 사용자 수 계산
    available_memory = 20 - used_mb  # 20MB 한도
    max_additional_users = int(available_memory / avg_memory_per_session)

    # 현재 + 추가 가능
    total_capacity = total_sessions + max_additional_users

    # 안전 마진 적용 (80%)
    safe_capacity = int(total_capacity * 0.8)

    return {
        "current_sessions": total_sessions,
        "used_memory": f"{used_mb:.1f}MB",
        "avg_memory_per_session": f"{avg_memory_per_session:.2f}MB",
        "max_additional_users": max_additional_users,
        "total_theoretical_capacity": total_capacity,
        "safe_capacity": safe_capacity,
        "recommendation": get_capacity_recommendation(total_sessions, safe_capacity)
    }

def get_capacity_recommendation(current: int, safe_capacity: int) -> str:
    """사용자 수에 따른 권장사항"""
    if current < safe_capacity * 0.5:
        return "여유 있음 - 추가 사용자 수용 가능"
    elif current < safe_capacity * 0.8:
        return "보통 - 모니터링 권장"
    elif current < safe_capacity:
        return "주의 - 세션 정리 고려"
    else:
        return "위험 - 즉시 세션 정리 필요"

def emergency_cleanup():
    """긴급 정리 - 기존 함수 유지"""
    if not client:
        return False

    try:
        client.flushdb()
        print("[EMERGENCY] 모든 세션 삭제됨")
        return True
    except Exception as e:
        print(f"[ERROR] 긴급 정리 실패: {e}")
        return False