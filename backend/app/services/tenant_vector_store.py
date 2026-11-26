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

# Keyword fallback matching: question words shorter than 3 characters
# and common stopwords carry no signal, so they are ignored when
# scoring chunks by keyword overlap with the question.
_KEYWORD_STOPWORDS = {
    "the", "and", "for", "what", "how", "are", "was", "were", "is", "in",
    "of", "to", "a", "an", "on", "at", "by", "with", "from", "that",
    "this", "it", "its", "as", "or", "do", "does", "did", "can", "could",
    "should", "would", "will", "shall", "may", "might", "i", "you", "he",
    "she", "we", "they", "me", "him", "us", "them", "my", "your", "his",
    "her", "our", "their", "am", "be", "been", "has", "have", "had",
    "not", "no", "yes", "if", "but", "so", "than", "then", "there",
    "here", "when", "where", "who", "which", "why", "any", "all",
    "each", "per", "via", "about", "into", "over", "under", "again",
}
_KEYWORD_SCAN_LIMIT = 2000


def _keyword_tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


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
        try:
            store.add_documents(documents)
        except Exception as e:
            if "dimension" in str(e).lower():
                try:
                    client = chromadb.PersistentClient(path=self.persist_directory)
                    client.delete_collection(name=collection_name_for_agent(agent_id))
                except Exception:
                    pass
                fresh_store = self.get_store(agent_id)
                fresh_store.add_documents(documents)
            else:
                raise e
        return len(documents)

    def similarity_search(self, agent_id: str, query: str, k: Optional[int] = None) -> List[Document]:
        retrieval_k = k or settings.RETRIEVAL_K
        store = self.get_store(agent_id)
        if store is None:
            return []

        try:
            hits = store.similarity_search(query, k=retrieval_k, filter={"agent_id": agent_id})
        except Exception as e:
            print(f"Vector similarity search failed for agent {agent_id}, falling back to keyword search: {e}")
            hits = []

        # Keyword fallback merge: top up with keyword-matching chunks when needed
        try:
            merged_hits = list(hits)
            if self._keyword_fallback_enabled():
                found = {self._source_key(hit) for hit in hits}
                if len(found) < retrieval_k:
                    merged_hits = hits + self._keyword_fallback_hits(
                        store, agent_id, query, found, retrieval_k - len(found))
            if not merged_hits:
                return merged_hits
            return self._expand_hits_with_neighbours(store, agent_id, merged_hits)
        except Exception as e:
            print(f"Retrieval post-processing failed, returning raw hits: {e}")
            return hits

    def count_chunks(self, agent_id: str) -> int:
        """Return total number of stored chunks for this agent. Used by debug endpoint."""
        try:
            client = chromadb.PersistentClient(path=self.persist_directory)
            col = client.get_or_create_collection(name=collection_name_for_agent(agent_id))
            return col.count()
        except Exception:
            return -1

    def search_with_scores(self, agent_id: str, query: str, k: int = 5) -> List[dict]:
        """Return chunks + their relevance scores for debug/diagnostic use."""
        store = self.get_store(agent_id)
        if store is None:
            return []
        try:
            scored = store.similarity_search_with_score(
                query, k=k, filter={"agent_id": agent_id}
            )
            return [
                {
                    "score": round(1.0 / (1.0 + max(0.0, float(dist))), 4),
                    "distance": round(float(dist), 4),
                    "document_name": (doc.metadata or {}).get("document_name", "?"),
                    "document_id": (doc.metadata or {}).get("document_id", "?"),
                    "chunk_index": (doc.metadata or {}).get("chunk_index"),
                    "preview": doc.page_content[:200] if doc.page_content else "",
                }
                for doc, dist in scored
            ]
        except Exception as e:
            return [{"error": str(e)}]

    @staticmethod
    def _keyword_fallback_enabled() -> bool:
        try:
            return bool(getattr(settings, "KEYWORD_FALLBACK", True))
        except Exception:
            return True

    def _source_key(self, doc: Document):
        """Identity of the source chunk a hit came from.

        Chunks with position metadata are identified by
        (document_id, chunk_index); older chunks without it fall back
        to their text, so duplicate rows of one source chunk count
        only once when measuring retrieval coverage.
        """
        meta = doc.metadata or {}
        doc_id = meta.get("document_id")
        idx = self._chunk_index_of(doc)
        if doc_id is not None and idx is not None:
            return ("chunk", doc_id, idx)
        return ("text", doc.page_content)

    def _keyword_fallback_hits(self, store, agent_id: str, query: str,
                               found: set, limit_count: int) -> List[Document]:
        """Top up retrieval with chunks sharing keywords with the query.

        Scans the agent's chunks (capped), scores each by how many of
        the question's meaningful words it contains, and returns the
        best-scoring chunks that vector search did not already find.
        Returns an empty list on any failure.
        """
        try:
            if limit_count <= 0:
                return []
            keywords = {w for w in _keyword_tokens(query)
                        if len(w) >= 3 and w not in _KEYWORD_STOPWORDS}
            if not keywords:
                return []
            try:
                result = store.get(where={"agent_id": agent_id},
                                   limit=_KEYWORD_SCAN_LIMIT)
            except TypeError:
                result = store.get(where={"agent_id": agent_id})
            texts = (result or {}).get("documents") or []
            metadatas = (result or {}).get("metadatas") or []
            scored = []
            for seq, (text, meta) in enumerate(zip(texts, metadatas)):
                if not text:
                    continue
                doc = Document(page_content=text, metadata=dict(meta or {}))
                if self._source_key(doc) in found:
                    continue
                score = len(keywords & set(_keyword_tokens(text)))
                if score > 0:
                    scored.append((-score,
                                   str((meta or {}).get("document_id") or ""),
                                   self._chunk_index_of(doc) or 0,
                                   seq, doc))
            scored.sort(key=lambda item: item[:4])
            return [item[4] for item in scored[:limit_count]]
        except Exception as e:
            print(f"Keyword fallback failed, keeping vector results only: {e}")
            return []

    @staticmethod
    def _chunk_index_of(doc: Document) -> Optional[int]:
        try:
            value = (doc.metadata or {}).get("chunk_index")
            return None if value is None else int(value)
        except (TypeError, ValueError):
            return None

    def _fetch_document_chunks(self, store, agent_id: str, document_id: str) -> dict:
        """Return {chunk_index: text} for every chunk of one document.

        Uses the LangChain Chroma wrapper's ``get`` with a ``where``
        filter on document_id + agent_id (the collection itself is
        already per-agent). Returns an empty dict on any failure.
        """
        try:
            result = store.get(where={"$and": [{"document_id": document_id},
                                               {"agent_id": agent_id}]})
        except Exception as e:
            print(f"Could not fetch chunks for document {document_id}: {e}")
            return {}
        texts = (result or {}).get("documents") or []
        metadatas = (result or {}).get("metadatas") or []
        chunk_map = {}
        for text, meta in zip(texts, metadatas):
            if text is None:
                continue
            try:
                idx = int((meta or {}).get("chunk_index"))
            except (TypeError, ValueError):
                continue
            chunk_map[idx] = text
        return chunk_map

    def _expand_hits_with_neighbours(self, store, agent_id: str, hits: List[Document]) -> List[Document]:
        try:
            neighbours = max(0, int(settings.CONTEXT_NEIGHBORS))
        except (TypeError, ValueError):
            neighbours = 1
        try:
            max_chars = int(settings.CONTEXT_MAX_CHARS)
        except (TypeError, ValueError):
            max_chars = 4000

        if neighbours <= 0:
            return hits

        def _join_chunks_cleanly(chunk_list: List[str]) -> str:
            if not chunk_list:
                return ""
            combined = chunk_list[0].strip()
            for next_chunk in chunk_list[1:]:
                next_chunk = next_chunk.strip()
                if not next_chunk:
                    continue
                words_combined = combined.split()
                words_next = next_chunk.split()
                max_ov = min(len(words_combined), len(words_next), 25)
                overlap_len = 0
                for ov in range(max_ov, 2, -1):
                    if words_combined[-ov:] == words_next[:ov]:
                        overlap_len = ov
                        break
                if overlap_len > 0:
                    combined += " " + " ".join(words_next[overlap_len:])
                else:
                    combined += " " + next_chunk
            return combined

        chunk_maps = {}   # document_id -> {chunk_index: text}
        doc_windows = {}  # document_id -> list of [start, end, rank, metadata]
        passages = []     # (rank, Document) for hits that stay unexpanded

        for rank, hit in enumerate(hits):
            meta = hit.metadata or {}
            doc_id = meta.get("document_id")
            idx = self._chunk_index_of(hit)
            if doc_id is None or idx is None:
                # Older chunks without position metadata stay as-is.
                passages.append((rank, hit))
                continue
            if doc_id not in chunk_maps:
                chunk_maps[doc_id] = self._fetch_document_chunks(store, agent_id, doc_id)
            if idx not in chunk_maps[doc_id]:
                passages.append((rank, hit))
                continue
            doc_windows.setdefault(doc_id, []).append(
                [idx - neighbours, idx + neighbours, rank, meta])

        # Merge overlapping windows per document into regions; each
        # chunk index is included exactly once per region.
        for doc_id, windows in doc_windows.items():
            cmap = chunk_maps[doc_id]
            windows.sort(key=lambda w: w[0])
            merged = []
            for start, end, rank, meta in windows:
                present = [i for i in range(start, end + 1) if i in cmap]
                if not present:
                    continue
                lo, hi = present[0], present[-1]
                if merged and lo <= merged[-1][1] + 1:
                    region = merged[-1]
                    region[1] = max(region[1], hi)
                    if rank < region[2]:
                        region[2] = rank
                        region[3] = meta
                else:
                    merged.append([lo, hi, rank, meta])
            for lo, hi, rank, meta in merged:
                text = _join_chunks_cleanly([cmap[i] for i in range(lo, hi + 1) if i in cmap])
                passages.append((rank, Document(page_content=text,
                                                metadata=dict(meta))))

        passages.sort(key=lambda item: item[0])

        # Cap the total context size; truncate the final region at a
        # word boundary if it would exceed the cap.
        results: List[Document] = []
        total = 0
        for _rank, doc in passages:
            text = doc.page_content or ""
            if max_chars > 0 and total + len(text) > max_chars:
                remaining = max_chars - total
                if remaining > 0:
                    cut = text[:remaining]
                    if " " in cut:
                        cut = cut[:cut.rfind(" ")].rstrip()
                    if cut:
                        results.append(Document(page_content=cut,
                                                metadata=doc.metadata))
                break
            results.append(doc)
            total += len(text)
        return results

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
