from fastapi import APIRouter
from typing import List
from app.schemas.recommend import UserProfile, MultiTurnRequest, RecommendedItem
from app.services.recommendation import get_recommendations
from app.utils.redis_client import get_session, save_session

router = APIRouter()

@router.post("/recommend", response_model=List[RecommendedItem])
def recommend(user: UserProfile):
    return get_recommendations(user)

@router.post("/multi-recommend", response_model=List[RecommendedItem])
def multi_recommend(req: MultiTurnRequest):
    session_id = req.session_id
    session_state = get_session(session_id)

    # 누적 상태 업데이트
    if req.age_group:
        session_state["age_group"] = req.age_group
    if req.interests:
        session_state["interests"] = list(set(session_state.get("interests", []) + req.interests))
    if req.time_usage:
        session_state["time_usage"] = list(set(session_state.get("time_usage", []) + req.time_usage))

    save_session(session_id, session_state)

    user_profile = UserProfile(**session_state)
    return get_recommendations(user_profile)