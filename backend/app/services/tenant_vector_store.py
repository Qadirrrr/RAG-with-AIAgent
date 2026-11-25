"""Per-agent Chroma vector store.

Tenant isolation: every agent gets its own Chroma collection named
``agent_<agent_id>`` (agent ids are uuid hex, so the name is safe), and
every chunk carries metadata ``workspace_id``, ``agent_id`` and
``document_id``. Retrieval and deletion always filter by agent_id, so
one customer's agent can never see another customer's documents.
The legacy global collection "rag_documents" is never used here.
"""
import re

import chromadb
from typing import List, Optional

try:
    from langchain_chroma import Chroma
except ImportError:  # pragma: no cover
    from langchain_community.vectorstores import Chroma

from langchain_core.documents import Document

from app.config import settings
from app.services.vector_store import vector_store_service


def collection_name_for_agent(agent_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", str(agent_id))
    return f"agent_{safe}"[:120]


class TenantVectorStore:
    def __init__(self):
        self.persist_directory = vector_store_service.persist_directory

    def get_embeddings(self):
        return vector_store_service.get_embeddings()

    def get_store(self, agent_id: str) -> Optional[Chroma]:
        embeddings = self.get_embeddings()
        if embeddings is None:
            return None
        return Chroma(
            collection_name=collection_name_for_agent(agent_id),
            embedding_function=embeddings,
            persist_directory=self.persist_directory,
        )

    def add_documents(self, agent_id: str, workspace_id: str, document_id: str, documents: List[Document]) -> int:
        store = self.get_store(agent_id)
        if store is None:
            raise ValueError("Embeddings are not available. Please check that Ollama is running on the server and that the embedding model is pulled (ollama pull bge-m3).")
        for doc in documents:
            doc.metadata["workspace_id"] = workspace_id
            doc.metadata["agent_id"] = agent_id
            doc.metadata["document_id"] = document_id
        store.add_documents(documents)
        return len(documents)

    def similarity_search(self, agent_id: str, query: str, k: int = 4) -> List[Document]:
        store = self.get_store(agent_id)
        if store is None:
            return []
        return store.similarity_search(query, k=k, filter={"agent_id": agent_id})

    def delete_document(self, agent_id: str, document_id: str) -> bool:
        try:
            client = chromadb.PersistentClient(path=self.persist_directory)
            collection = client.get_or_create_collection(name=collection_name_for_agent(agent_id))
            collection.delete(where={"$and": [{"document_id": document_id}, {"agent_id": agent_id}]})
            return True
        except Exception as e:
            print(f"Error deleting document {document_id} from tenant Chroma: {e}")
            return False

    def delete_agent_collection(self, agent_id: str) -> bool:
        try:
            client = chromadb.PersistentClient(path=self.persist_directory)
            client.delete_collection(name=collection_name_for_agent(agent_id))
            return True
        except Exception:
            return False


tenant_vector_store = TenantVectorStore()
