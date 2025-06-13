from langchain_core.prompts import ChatPromptTemplate
from app.prompts.base_prompt import BASE_PROMPTS
from app.prompts.plan_prompt import PLAN_PROMPTS
from app.prompts.subscription_prompt import SUBSCRIPTION_PROMPT

def get_prompt_template(intent: str, tone: str = "general") -> ChatPromptTemplate:
    """
    인텐트와 말투에 따른 프롬프트 템플릿 반환
    """
    # tone 검증
    if tone not in ["general", "muneoz"]:
        tone = "general"

    # 요금제 관련
    if intent.startswith("phone_plan"):
        prompt_dict = PLAN_PROMPTS.get(intent, {})
        if isinstance(prompt_dict, dict) and tone in prompt_dict:
            prompt_text = prompt_dict[tone]
        else:
            prompt_text = PLAN_PROMPTS.get(intent, BASE_PROMPTS["default"][tone])
        return ChatPromptTemplate.from_template(prompt_text)

    # 구독 서비스 관련
    elif intent in ["subscription_recommend", "subscription_multi"]:
        if isinstance(SUBSCRIPTION_PROMPT, dict) and tone in SUBSCRIPTION_PROMPT:
            prompt_text = SUBSCRIPTION_PROMPT[tone]
        else:
            prompt_text = SUBSCRIPTION_PROMPT
        return ChatPromptTemplate.from_template(prompt_text)

    # 기본 응답 (인사, 문의, 추천 등)
    else:
        prompt_dict = BASE_PROMPTS.get(intent, BASE_PROMPTS["default"])
        if isinstance(prompt_dict, dict) and tone in prompt_dict:
            prompt_text = prompt_dict[tone]
        else:
            prompt_text = BASE_PROMPTS["default"][tone]
        return ChatPromptTemplate.from_template(prompt_text)