from langchain_openai import ChatOpenAI
import os

def get_chat_model():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        streaming=True,
        api_key=os.getenv("OPENAI_API_KEY")
    )
