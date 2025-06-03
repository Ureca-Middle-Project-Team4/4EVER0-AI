from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest
from app.services.handle_chat import handle_chat

router = APIRouter()

@router.post("/chat")
async def chat(req: ChatRequest):
    stream_fn = await handle_chat(req)
    return StreamingResponse(stream_fn(), media_type="text/plain")
