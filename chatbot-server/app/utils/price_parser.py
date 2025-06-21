import re
from typing import Optional, Tuple, Union

def parse_budget_to_number(text: str) -> Optional[int]:
    """'3만원대', '5만원 이하' 등을 숫자값(예: 30000)으로 변환"""
    text = text.replace(",", "").replace(" ", "")
    match = re.search(r"(\d+)\s*만", text)
    if match:
        amount = int(match.group(1)) * 10000
    else:
        match = re.search(r"(\d{4,6})", text)
        amount = int(match.group(1)) if match else None

    if "이하" in text or "미만" in text or "이내" in text:
        return amount
    if "이상" in text or "초과" in text:
        return amount + 1
    if "정도" in text or "대" in text or "쯤" in text:
        return amount
    return amount

def parse_budget_range(text: str) -> Tuple[Optional[int], Optional[str]]:
    """텍스트 예산 → (숫자, 방향) 튜플로 파싱"""
    text = text.strip()
    direction = "max"
    if "이상" in text or "보다 많" in text:
        direction = "min"
    elif "이하" in text or "이내" in text or "보다 적" in text:
        direction = "max"

    match = re.search(r"(\d+)\s*만원", text)
    if match:
        return int(match.group(1)) * 10000, direction
    return None, direction