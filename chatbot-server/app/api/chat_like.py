from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.chat import LikesChatRequest
from app.services.handle_chat_likes import handle_chat_likes

router = APIRouter()

@router.post("/chat/likes")
async def chat_likes(req: LikesChatRequest):
    stream_fn = await handle_chat_likes(req)
    return StreamingResponse(stream_fn(), media_type="text/plain")
