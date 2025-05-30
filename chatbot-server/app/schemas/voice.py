from pydantic import BaseModel
from typing import Optional

class VoiceChatResponse(BaseModel):
    user_text: str
    gpt_text: str
    audio_url: Optional[str]
