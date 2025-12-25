from config import settings
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

def get_llm(provider: str):
    if provider == "ollama":
        return ChatOllama(model=settings.OLLAMA_MODEL, temperature=0.2)
    return ChatGroq(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL, temperature=0.2)
