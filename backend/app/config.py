import os
import dotenv
from typing import Optional, Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG AI Agent API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Gemini Configuration
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"

    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    UPLOAD_DIRECTORY: str = "./data/uploads"
    
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

    def get_gemini_api_key(self) -> str:
        self._reload_env()
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or self.GEMINI_API_KEY or self.GOOGLE_API_KEY
        if key and key.strip() and "your_" not in key:
            return key.strip()
        return ""

    def get_openai_api_key(self) -> str:
        self._reload_env()
        key = os.environ.get("OPENAI_API_KEY") or self.OPENAI_API_KEY
        if key and key.strip() and "your_" not in key:
            return key.strip()
        return ""

    def get_active_provider(self) -> Literal["gemini", "openai", "none"]:
        if self.get_gemini_api_key():
            return "gemini"
        if self.get_openai_api_key():
            return "openai"
        return "none"

    def get_active_model(self) -> str:
        provider = self.get_active_provider()
        if provider == "gemini":
            return self.GEMINI_MODEL
        if provider == "openai":
            return self.OPENAI_MODEL
        return self.GEMINI_MODEL

    def get_active_embedding_model(self) -> str:
        provider = self.get_active_provider()
        if provider == "gemini":
            return self.GEMINI_EMBEDDING_MODEL
        if provider == "openai":
            return self.OPENAI_EMBEDDING_MODEL
        return self.GEMINI_EMBEDDING_MODEL

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
