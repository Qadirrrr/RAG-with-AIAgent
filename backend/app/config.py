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

    # Document chunking at ingestion time. Chunks are word-based: each
    # chunk holds at most CHUNK_WORDS words, and consecutive chunks
    # share CHUNK_WORD_OVERLAP words so context is not lost at the
    # boundaries. Small, focused chunks keep each retrieved section
    # precise. Changing these only affects documents uploaded
    # afterwards; existing documents keep the chunks they were ingested
    # with until they are re-uploaded.
    CHUNK_WORDS: int = 20
    CHUNK_WORD_OVERLAP: int = 5

    # How many knowledge sections are retrieved per question and given
    # to the model. A deeper retrieval lets the model combine facts
    # from across a document instead of answering from a few sections.
    RETRIEVAL_K: int = 10

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
