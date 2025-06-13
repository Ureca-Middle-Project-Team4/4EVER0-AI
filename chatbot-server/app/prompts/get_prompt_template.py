from langchain_core.prompts import ChatPromptTemplate
from app.prompts.base_prompt import BASE_PROMPTS
from app.prompts.plan_prompt import PLAN_PROMPTS
from app.prompts.subscription_prompt import SUBSCRIPTION_PROMPT

def get_prompt_template(intent: str) -> ChatPromptTemplate:
    # 요금제 관련
    if intent.startswith("phone_plan"):
        return ChatPromptTemplate.from_template(PLAN_PROMPTS.get(intent, BASE_PROMPTS["default"]))

    # 구독 서비스 관련
    elif intent in ["subscription_recommend", "subscription_multi"]:
        return ChatPromptTemplate.from_template(SUBSCRIPTION_PROMPT)

    # 기본 응답 (인사, 문의, 추천 등)
    else:
        return ChatPromptTemplate.from_template(BASE_PROMPTS.get(intent, BASE_PROMPTS["default"]))