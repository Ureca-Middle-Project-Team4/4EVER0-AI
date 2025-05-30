from openai import OpenAI
from gtts import gTTS
import tempfile
import os
from uuid import uuid4
from datetime import datetime

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def handle_voice_chat(file):
    # 1. UploadFile을 임시 wav 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # 2. Whisper를 이용한 한국어 STT
    with open(tmp_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ko"
        )
    user_text = transcript.text

    # 3. GPT로 대화 응답 생성
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_text}],
    )
    gpt_text = res.choices[0].message.content

    # 4. GPT 응답을 TTS(mp3)로 변환 (한국어 TTS)
    tts = gTTS(gpt_text, lang="ko")
    filename = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}.mp3"

    # 5. static/audio 디렉터리로 mp3 저장
    static_dir = os.path.join("static", "audio")
    os.makedirs(static_dir, exist_ok=True)
    tts_path = os.path.join(static_dir, filename)
    tts.save(tts_path)

    audio_url = f"/static/audio/{filename}"

    return {
        "user_text": user_text,
        "gpt_text": gpt_text,
        "audio_url": audio_url
    }
