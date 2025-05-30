from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.openai_service import ask_gpt

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    gpt_response = await ask_gpt(request.message)
    return ChatResponse(response=gpt_response)
