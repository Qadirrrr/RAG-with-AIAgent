import os
import dotenv
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG AI Agent API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Self-hosted Ollama Configuration (the only AI provider, no cloud
    # API key needed). Chat uses the Ollama server at OLLAMA_BASE_URL
    # with a Qwen model; embeddings use the BGE model through Ollama.
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    # Embeddings are always self-hosted BGE via Ollama (model bge-m3).
    # The variable is kept for compatibility; only "bge" is supported.
    EMBEDDING_PROVIDER: str = "bge"
    BGE_EMBEDDING_MODEL: str = "bge-m3"

    # Agent mode (LangGraph): maximum tool-calling steps per answer
    AGENT_MAX_STEPS: int = 5

    # Document chunking at ingestion time.
    # Small, focused chunks (~80 words) preserve complete sentences
    # and concepts without breaking clauses mid-sentence.
    CHUNK_WORDS: int = 80
    CHUNK_WORD_OVERLAP: int = 15

    # Number of knowledge chunks retrieved per question.
    # 8 chunks with 1 neighbor ensures high recall for both old 20-word
    # chunks and new 80-word semantic chunks.
    RETRIEVAL_K: int = 8

    # Context expansion: 1 neighbor before/after preserves full context
    # around matched sections without missing adjacent details.
    CONTEXT_NEIGHBORS: int = 1
    CONTEXT_MAX_CHARS: int = 4500

    # Keyword fallback: when vector search finds fewer distinct chunks
    # than requested, chunks are also matched by keyword overlap.
    KEYWORD_FALLBACK: bool = True

    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    UPLOAD_DIRECTORY: str = "./data/uploads"

    # SaaS settings
    DATABASE_URL: str = ""
    JWT_SECRET: str = ""
    JWT_EXPIRE_HOURS: int = 24
    CORS_ORIGINS: str = "*"
    SUPER_ADMIN_EMAIL: str = ""

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    def _reload_env(self):
        env_paths = [
            os.path.join(os.getcwd(), "backend", ".env"),
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        ]
        for p in env_paths:
            if os.path.exists(p):
                dotenv.load_dotenv(p, override=True)
                break

    def get_active_provider(self) -> str:
        """The platform has exactly one AI provider: self-hosted Ollama."""
        return "ollama"

    def get_active_model(self) -> str:
        return self.OLLAMA_MODEL

    def get_active_embedding_model(self) -> str:
        return self.BGE_EMBEDDING_MODEL

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
