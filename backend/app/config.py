import os
import dotenv
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Chatbot API"
    VERSION: str = "2.0.0"

    # Self-hosted Ollama (no cloud API key needed)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    BGE_EMBEDDING_MODEL: str = "bge-m3"

    # RAG tuning
    CHUNK_WORDS: int = 80
    CHUNK_WORD_OVERLAP: int = 15
    RETRIEVAL_K: int = 8
    CONTEXT_NEIGHBORS: int = 1
    CONTEXT_MAX_CHARS: int = 4500

    # Storage
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    UPLOAD_DIRECTORY: str = "./data/uploads"

    CORS_ORIGINS: str = "*"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
