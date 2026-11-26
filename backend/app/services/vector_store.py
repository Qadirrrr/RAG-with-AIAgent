import os
from typing import List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import chromadb
import httpx

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from app.config import settings


class OllamaBgeEmbeddings(Embeddings):
    """BGE embeddings served by a self-hosted Ollama instance.

    Uses a persistent keep-alive HTTP client and leverages Ollama's
    batch embedding API (/api/embed) for maximum throughput and speed,
    falling back to parallel /api/embeddings if needed.
    """

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

    def _embed_batch_api(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Try Ollama's modern batch /api/embed endpoint."""
        try:
            resp = self._client.post(
                "/api/embed",
                json={"model": self.model, "input": texts},
            )
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get("embeddings")
                if embeddings and len(embeddings) == len(texts):
                    return embeddings
        except Exception:
            pass
        return None

    def _embed_single(self, text: str) -> List[float]:
        """Embed a single string via /api/embeddings with keep-alive client."""
        resp = self._client.post(
            "/api/embeddings",
            json={"model": self.model, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # 1. Try batching chunks via /api/embed in batches of 16
        batch_size = 16
        all_embeddings: List[List[float]] = []
        can_use_batch_api = True

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            if can_use_batch_api:
                batch_res = self._embed_batch_api(batch)
                if batch_res is not None:
                    all_embeddings.extend(batch_res)
                    continue
                else:
                    can_use_batch_api = False

            # Fallback to parallel calls
            with ThreadPoolExecutor(max_workers=min(5, len(batch))) as executor:
                res = list(executor.map(self._embed_single, batch))
                all_embeddings.extend(res)

        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        # Quick query embedding
        try:
            batch_res = self._embed_batch_api([text])
            if batch_res and len(batch_res) == 1:
                return batch_res[0]
        except Exception:
            pass
        return self._embed_single(text)


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
        if self._embeddings is None or self._cached_provider != "bge":
            self._embeddings = OllamaBgeEmbeddings(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.BGE_EMBEDDING_MODEL,
            )
            self._cached_provider = "bge"
            self._cached_key = None
            self._vector_store = None
        return self._embeddings

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
            raise ValueError("Embeddings are not available. Please check that Ollama is running on the server and that the embedding model is pulled (ollama pull bge-m3).")
        
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

    def similarity_search(self, query: str, k: Optional[int] = None) -> List[Document]:
        vector_store = self.get_vector_store()
        if vector_store is None:
            return []
        retrieval_k = k or settings.RETRIEVAL_K
        return vector_store.similarity_search(query, k=retrieval_k)

    def check_health(self) -> bool:
        try:
            client = chromadb.PersistentClient(path=self.persist_directory)
            client.heartbeat()
            return True
        except Exception:
            return False


vector_store_service = VectorStoreService()
