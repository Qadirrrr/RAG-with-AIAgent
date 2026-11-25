import os
from typing import List, Optional, Any
import chromadb
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from app.config import settings


class OllamaBgeEmbeddings(Embeddings):
    """BGE embeddings served by a self-hosted Ollama instance.

    Calls Ollama's /api/embeddings endpoint with the configured BGE
    model (default bge-m3). No cloud API key is involved.
    """

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _embed(self, text: str) -> List[float]:
        import httpx
        resp = httpx.post(f"{self.base_url}/api/embeddings",
                          json={"model": self.model, "prompt": text}, timeout=60)
        resp.raise_for_status()
        return resp.json()["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

class VectorStoreService:
    def __init__(self):
        self.persist_directory = os.path.abspath(settings.CHROMA_PERSIST_DIRECTORY)
        os.makedirs(self.persist_directory, exist_ok=True)
        self.collection_name = "rag_documents"
        self._vector_store: Optional[Chroma] = None
        self._embeddings: Optional[Any] = None
        self._cached_provider: Optional[str] = None
        self._cached_key: Optional[str] = None

    def get_embeddings(self) -> Optional[Any]:
        # EMBEDDING_PROVIDER=bge selects self-hosted BGE via Ollama and
        # takes priority over the cloud providers. The default ("gemini")
        # keeps the existing behaviour so current collections keep working.
        if (settings.EMBEDDING_PROVIDER or "").lower() == "bge":
            if self._embeddings is None or self._cached_provider != "bge":
                self._embeddings = OllamaBgeEmbeddings(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.BGE_EMBEDDING_MODEL,
                )
                self._cached_provider = "bge"
                self._cached_key = None
                self._vector_store = None
            return self._embeddings

        provider = settings.get_active_provider()

        if provider == "gemini":
            key = settings.get_gemini_api_key()
            if self._embeddings is None or self._cached_provider != "gemini" or self._cached_key != key:
                self._embeddings = GoogleGenerativeAIEmbeddings(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    google_api_key=key
                )
                self._cached_provider = "gemini"
                self._cached_key = key
                self._vector_store = None
            return self._embeddings

        elif provider == "openai":
            key = settings.get_openai_api_key()
            if self._embeddings is None or self._cached_provider != "openai" or self._cached_key != key:
                self._embeddings = OpenAIEmbeddings(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    openai_api_key=key
                )
                self._cached_provider = "openai"
                self._cached_key = key
                self._vector_store = None
            return self._embeddings

        return None

    def get_vector_store(self) -> Optional[Chroma]:
        embeddings = self.get_embeddings()
        if embeddings is None:
            return None
        if self._vector_store is None:
            self._vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=embeddings,
                persist_directory=self.persist_directory
            )
        return self._vector_store

    def add_documents(self, documents: List[Document]) -> int:
        vector_store = self.get_vector_store()
        if vector_store is None:
            raise ValueError("No AI API Key is configured. Please set your GEMINI_API_KEY in backend/.env")
        
        vector_store.add_documents(documents)
        return len(documents)

    def delete_document(self, document_id: str) -> bool:
        try:
            client = chromadb.PersistentClient(path=self.persist_directory)
            collection = client.get_or_create_collection(name=self.collection_name)
            collection.delete(where={"document_id": document_id})
            self._vector_store = None
            return True
        except Exception as e:
            print(f"Error deleting document {document_id} from Chroma: {e}")
            return False

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        vector_store = self.get_vector_store()
        if vector_store is None:
            return []
        return vector_store.similarity_search(query, k=k)

    def check_health(self) -> bool:
        try:
            client = chromadb.PersistentClient(path=self.persist_directory)
            client.heartbeat()
            return True
        except Exception:
            return False

vector_store_service = VectorStoreService()
