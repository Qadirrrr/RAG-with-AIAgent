"""Core RAG service — single agent, no workspace/auth complexity."""
import logging
import re
from typing import List, Dict, Any

import httpx
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import settings
from app.services.document_loader import document_loader_service
from app.services.vector_store import vector_store_service

logger = logging.getLogger("rag_service")

# ── Meta-prefix cleaner ───────────────────────────────────────────────────────
_META_RE = re.compile(
    r"^\s*(?:based\s+on|according\s+to|from|per|using|in|as\s+per|drawing\s+from)\s+"
    r"(?:the\s+|my\s+|your\s+)?"
    r"(?:(?:provided|given|available|above|shared|uploaded|stored|following)\s+)*"
    r"(?:knowledge(?:\s+base)?|reference(?:\s+information)?|information|context|data|"
    r"facts|details|document|documents|text|source|sources)\s*[,:\-]?\s*",
    re.IGNORECASE,
)
_SRC_RE = re.compile(r"\s*[\(\[]\s*Source\s*:[^\)\]]+[\)\]]", re.IGNORECASE)


def _clean(text: str) -> str:
    if not text:
        return text
    text = _SRC_RE.sub("", text)
    for _ in range(3):
        next_t = _META_RE.sub("", text, count=1).lstrip()
        if next_t == text:
            break
        text = next_t
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text.strip()


class RAGService:
    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            try:
                from langchain_ollama import ChatOllama
                self._llm = ChatOllama(
                    model=settings.OLLAMA_MODEL,
                    temperature=0.1,
                    base_url=settings.OLLAMA_BASE_URL.rstrip("/"),
                    keep_alive="30m",
                    num_ctx=4096,
                    num_predict=512,
                )
            except Exception as e:
                logger.error(f"Failed to init ChatOllama: {e}")
        return self._llm

    # ── Ingest ────────────────────────────────────────────────────────────────

    def ingest_file(self, file_path: str, doc_id: str, filename: str) -> int:
        """Load, chunk, embed and store a document. Returns chunk count."""
        chunks = document_loader_service.load_and_split(file_path, doc_id, filename)
        if not chunks:
            raise ValueError("No text could be extracted from the document.")

        # Tag each chunk with doc metadata
        for chunk in chunks:
            chunk.metadata["doc_id"] = doc_id
            chunk.metadata["document_id"] = doc_id
            chunk.metadata["document_name"] = filename

        vector_store_service.add_documents(chunks)
        return len(chunks)

    def delete_document(self, doc_id: str):
        """Remove all chunks for a document from the vector store."""
        vector_store_service.delete_by_metadata("doc_id", doc_id)

    # ── Answer ────────────────────────────────────────────────────────────────

    async def answer(self, question: str, history: List[Dict[str, str]] = None) -> str:
        """RAG answer: retrieve → prompt → LLM → clean."""
        llm = self._get_llm()
        if llm is None:
            return "The AI model is currently unavailable. Please try again later."

        # 1. Retrieve relevant chunks
        try:
            docs = vector_store_service.similarity_search(question, k=settings.RETRIEVAL_K)
        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            docs = []

        # 2. Build prompt
        if docs:
            context = "\n\n".join(
                (d.page_content or "").strip() for d in docs if (d.page_content or "").strip()
            )
            system_msg = (
                "You are a professional and helpful assistant.\n"
                "Rules:\n"
                "1. Answer accurately using only the Facts below.\n"
                "2. Include exact names, numbers, dates, and details from the Facts.\n"
                "3. Answer directly and naturally — as if you personally know these facts.\n"
                "4. CRITICAL: NEVER start with 'Based on', 'According to', 'From the', "
                "'Using the', or any phrase referencing knowledge/documents/context/source.\n"
                "5. If the Facts are completely unrelated to the question, say: "
                "'I do not have that information.'\n"
                "6. Format with short paragraphs or bullet points."
            )
            user_content = f"Facts:\n{context}\n\nQuestion:\n{question}"
        else:
            system_msg = (
                "You are a helpful assistant. "
                "No documents have been uploaded yet, or the question is unrelated to available data. "
                "Politely tell the user you do not have information to answer this question."
            )
            user_content = question

        messages = [SystemMessage(content=system_msg)]
        for msg in (history or [])[-6:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
        messages.append(HumanMessage(content=user_content))

        # 3. Call LLM
        try:
            result = await llm.ainvoke(messages)
            text = result.content if isinstance(result.content, str) else str(result.content)
            return _clean(text.strip()) or "I do not have that information."
        except Exception as e:
            err = str(e)
            logger.error(f"LLM call failed: {err}", exc_info=True)
            if "timeout" in err.lower() or "504" in err:
                return "The assistant is taking longer than expected. Please try again."
            return "Something went wrong while generating a response. Please try again."


rag_service = RAGService()
