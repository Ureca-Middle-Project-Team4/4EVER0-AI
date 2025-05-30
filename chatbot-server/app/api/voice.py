from fastapi import APIRouter, UploadFile, File
from app.schemas.voice import VoiceChatResponse
from app.services.voice_service import handle_voice_chat

router = APIRouter()

@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(file: UploadFile = File(...)):
    return await handle_voice_chat(file)
