from langchain_core.prompts import ChatPromptTemplate
from app.prompts.base_prompt import BASE_PROMPTS
from app.prompts.plan_prompt import PLAN_PROMPTS
from app.prompts.subscription_prompt import SUBSCRIPTION_PROMPT

def get_prompt_template(intent: str) -> ChatPromptTemplate:
    if intent.startswith("phone_plan"):
        return ChatPromptTemplate.from_template(PLAN_PROMPTS.get(intent, BASE_PROMPTS["default"]))
    elif intent == "subscription_recommend":
        return ChatPromptTemplate.from_template(SUBSCRIPTION_PROMPT)
    else:
        return ChatPromptTemplate.from_template(BASE_PROMPTS.get(intent, BASE_PROMPTS["default"]))
