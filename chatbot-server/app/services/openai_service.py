import openai
from app.config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

async def ask_gpt(message: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}]
    )
    return response["choices"][0]["message"]["content"]
