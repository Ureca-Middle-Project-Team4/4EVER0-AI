from app.db.ubti_types_db import get_all_ubti_types
from app.prompts.ubti_prompt import get_ubti_prompt
from app.utils.langchain_client import get_chat_model

async def analyze_ubti(answers: list[str]) -> str:
    prompt = get_ubti_prompt().format(
        message="\n".join(answers),
        ubti_types=get_all_ubti_types()
    )
    response = await get_chat_model().ainvoke(prompt)
    return response.content
