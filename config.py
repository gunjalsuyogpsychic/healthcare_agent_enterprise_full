import os
from dataclasses import dataclass

@dataclass
class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    DB_PATH: str = os.getenv("DB_PATH", "storage/healthcare.db")
    FAISS_DIR: str = os.getenv("FAISS_DIR", "storage/faiss_index")
    PDF_SOURCES_DIR: str = os.getenv("PDF_SOURCES_DIR", "data/pdf_sources")
    RECORDS_XLSX: str = os.getenv("RECORDS_XLSX", "data/records.xlsx")

settings = Settings()
