from fastapi import APIRouter
from app.schemas.recommend import UserProfile, RecommendedItem
from app.services.recommendation import get_recommendations

router = APIRouter()

@router.post("/recommend", response_model=list[RecommendedItem])
def recommend(user: UserProfile):
    return get_recommendations(user)


# app/main.py 에 추가
from fastapi import FastAPI
from app.api import chat, recommend

app = FastAPI()

app.include_router(chat.router, prefix="/chat")
app.include_router(recommend.router, prefix="/api")
