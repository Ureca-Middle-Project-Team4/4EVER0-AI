import redis
import json
import os
import time
from typing import Dict, Any

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))

# 메모리 절약 설정
MEMORY_LIMIT_MB = int(os.getenv("REDIS_MEMORY_LIMIT_MB", "50"))  # 50MB 제한
SESSION_TTL = int(os.getenv("SESSION_TTL", "600"))  # 10분으로 단축
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "500"))  # 최대 세션 수 제한

print(f"[DEBUG] Redis 메모리 최적화 모드 - TTL: {SESSION_TTL}초, 최대 세션: {MAX_SESSIONS}개")

def create_redis_client():
    """Redis 클라이언트 생성 - 메모리 최적화 설정"""
    try:
        client = redis.Redis(
            host=redis_host, 
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3
        )
        
        # Redis 메모리 설정 최적화
        try:
            # maxmemory 설정 (50MB)
            client.config_set('maxmemory', f'{MEMORY_LIMIT_MB}mb')
            # LRU 정책으로 오래된 키 자동 삭제
            client.config_set('maxmemory-policy', 'allkeys-lru')
            print(f"[SUCCESS] Redis 메모리 설정 완료 - {MEMORY_LIMIT_MB}MB 제한")
        except Exception as e:
            print(f"[WARNING] Redis 설정 실패 (권한 문제일 수 있음): {e}")
        
        client.ping()
        return client
    except Exception as e:
        print(f"[ERROR] Redis 연결 실패: {e}")
        return None

client = create_redis_client()

def get_session(session_id: str) -> dict:
    """세션 조회 - 압축된 데이터 사용"""
    if not session_id or not client:
        return {}
    
    try:
        data = client.get(session_id)
        if not data:
            return {}
        
        # JSON 파싱
        session_data = json.loads(data)
        
        # 불필요한 키 제거 (메모리 절약)
        cleaned_data = clean_session_data(session_data)
        
        print(f"[DEBUG] 세션 조회: {session_id} (크기: {len(data)} bytes)")
        return cleaned_data
        
    except Exception as e:
        print(f"[ERROR] 세션 조회 실패: {e}")
        return {}

def save_session(session_id: str, data: dict):
    """세션 저장 - 메모리 최적화"""
    if not client:
        return False
    
    try:
        # 데이터 정리 및 압축
        cleaned_data = clean_session_data(data)
        compressed_data = compress_session_data(cleaned_data)
        
        # JSON 직렬화
        json_data = json.dumps(compressed_data, ensure_ascii=False, separators=(',', ':'))
        
        # 크기 체크 (5KB 초과 시 경고)
        if len(json_data) > 5120:
            print(f"[WARNING] 세션 크기가 큼: {len(json_data)} bytes")
            # 큰 데이터는 더 짧은 TTL 적용
            ttl = SESSION_TTL // 2
        else:
            ttl = SESSION_TTL
        
        # Redis에 저장
        client.set(session_id, json_data, ex=ttl)

        if hash(session_id) % 10 == 0:
            cleanup_old_sessions()
        
        print(f"[DEBUG] 세션 저장: {session_id} (크기: {len(json_data)} bytes, TTL: {ttl}초)")
        return True
        
    except Exception as e:
        print(f"[ERROR] 세션 저장 실패: {e}")
        return False

def clean_session_data(data: dict) -> dict:
    """세션 데이터 정리 - 불필요한 키 제거"""
    if not isinstance(data, dict):
        return {}
    
    # 보존할 핵심 키만 유지
    essential_keys = {
        'phone_plan_flow_step', 'subscription_flow_step',
        'user_info', 'history'
    }
    
    cleaned = {}
    for key, value in data.items():
        if key in essential_keys:
            if key == 'history':
                # 히스토리는 최근 5개만 유지
                if isinstance(value, list):
                    cleaned[key] = value[-5:]
                else:
                    cleaned[key] = value
            else:
                cleaned[key] = value
    
    return cleaned

def compress_session_data(data: dict) -> dict:
    """세션 데이터 압축 - 키 이름 단축"""
    if not data:
        return {}
    
    # 키 이름 단축으로 메모리 절약
    key_mapping = {
        'phone_plan_flow_step': 'pfs',
        'subscription_flow_step': 'sfs', 
        'user_info': 'ui',
        'history': 'h'
    }
    
    compressed = {}
    for key, value in data.items():
        short_key = key_mapping.get(key, key)
        compressed[short_key] = value
    
    return compressed

def decompress_session_data(data: dict) -> dict:
    """압축된 세션 데이터 복원"""
    if not data:
        return {}
    
    # 단축된 키 이름 복원
    reverse_mapping = {
        'pfs': 'phone_plan_flow_step',
        'sfs': 'subscription_flow_step',
        'ui': 'user_info', 
        'h': 'history'
    }
    
    decompressed = {}
    for key, value in data.items():
        full_key = reverse_mapping.get(key, key)
        decompressed[full_key] = value
    
    return decompressed

def cleanup_old_sessions():
    """오래된 세션 정리"""
    if not client:
        return
    
    try:
        # 전체 키 수 확인
        total_keys = client.dbsize()
        
        if total_keys > MAX_SESSIONS:
            print(f"[WARNING] 세션 수 초과 ({total_keys}개), 정리 시작")
            
            # 샘플링해서 일부 키 삭제 (전체 스캔은 성능 이슈)
            keys_to_delete = []
            for key in client.scan_iter(count=100):
                # TTL이 짧은 키들 우선 삭제
                ttl = client.ttl(key)
                if ttl < 60 or len(keys_to_delete) >= 100:  # 1분 미만 또는 100개 수집
                    keys_to_delete.append(key)
                    if len(keys_to_delete) >= 100:
                        break
            
            if keys_to_delete:
                client.delete(*keys_to_delete)
                print(f"[DEBUG] {len(keys_to_delete)}개 세션 정리 완료")
                
    except Exception as e:
        print(f"[ERROR] 세션 정리 실패: {e}")

def delete_session(session_id: str):
    """세션 삭제"""
    if client:
        try:
            client.delete(session_id)
            print(f"[DEBUG] 세션 삭제: {session_id}")
        except Exception as e:
            print(f"[ERROR] 세션 삭제 실패: {e}")

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