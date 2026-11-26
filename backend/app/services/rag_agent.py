import logging
import os
import time
from typing import List, Dict, Any, Optional, Set

import httpx
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.config import settings
from app.services.vector_store import vector_store_service
from app.services.storage import storage_service
from app.models.schemas import ChatResponse, DocumentSource

logger = logging.getLogger("rag_agent")

# Provider -> allowed chat models (validated again in routes/agents.py).
# Ollama is the only provider. The set holds known-good defaults, but
# any qwen* model string is also accepted (see is_model_allowed),
# because the exact tag installed on the self-hosted server is chosen
# by the operator.
ALLOWED_MODELS = {
    "ollama": {"qwen2.5:7b", "qwen2.5:3b", "qwen2.5:14b", "qwen2.5:32b", "qwen3:8b"},
}


def is_model_allowed(provider: str, model: str) -> bool:
    if provider != "ollama":
        return False
    return bool(model) and (model in ALLOWED_MODELS["ollama"] or model.startswith("qwen"))


# ---------------------------------------------------------------------------
# Pulled-model fallback
#
# A chatbot can be stored with any qwen* tag, but the self-hosted Ollama
# server only serves models that were actually pulled onto it. Asking
# Ollama for an unpulled model fails every chat with a 404 "model not
# found", so before building the LLM we check the server's pulled list
# (GET /api/tags, the same endpoint the health route uses) and fall back
# to the configured default model when the stored one is missing. The
# stored model in the DB is never changed; the fallback happens at call
# time only. The pulled list is cached briefly so chat is not slowed by
# an extra request on every message. If the tags fetch fails (Ollama
# unreachable), the resolver returns the requested model unchanged and
# the existing unavailable/error handling runs exactly as before.
# ---------------------------------------------------------------------------
_TAGS_TIMEOUT_SECONDS = 3.0
_TAGS_CACHE_SECONDS = 30.0
_pulled_models_cache: Dict[str, Any] = {"names": None, "fetched_at": 0.0}


def _get_pulled_model_names() -> Optional[Set[str]]:
    """Names of the models pulled on the Ollama server, or None on failure."""
    now = time.monotonic()
    cached = _pulled_models_cache["names"]
    if cached is not None and now - _pulled_models_cache["fetched_at"] < _TAGS_CACHE_SECONDS:
        return cached
    try:
        resp = httpx.get(settings.OLLAMA_BASE_URL.rstrip("/") + "/api/tags",
                         timeout=_TAGS_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            return None
        names = {
            entry.get("name", "")
            for entry in resp.json().get("models", [])
            if isinstance(entry, dict) and entry.get("name")
        }
    except Exception:
        return None
    _pulled_models_cache["names"] = names
    _pulled_models_cache["fetched_at"] = now
    return names


def _is_pulled(model: str, pulled: Set[str]) -> bool:
    if model in pulled:
        return True
    # Ollama lists untagged models with a ":latest" suffix, so a stored
    # bare name (for example "qwen2.5") also matches "qwen2.5:latest".
    return ":" not in model and f"{model}:latest" in pulled


def resolve_chat_model(model: Optional[str]) -> str:
    """Resolve the model a chat should actually run with.

    Returns the stored model when it is pulled on the Ollama server.
    When it is not pulled, falls back to settings.OLLAMA_MODEL if that
    one is pulled. When the pulled list cannot be fetched, returns the
    stored model unchanged so a down server is handled by the existing
    error paths, not masked here.
    """
    requested = model if is_model_allowed("ollama", model or "") else settings.OLLAMA_MODEL
    pulled = _get_pulled_model_names()
    if pulled is None or _is_pulled(requested, pulled):
        return requested
    default = settings.OLLAMA_MODEL
    if _is_pulled(default, pulled):
        return default
    return requested


class RAGAgentService:
    def __init__(self):
        pass

    def _get_llm(self, provider: Optional[str] = None, model: Optional[str] = None,
                 temperature: float = 0.2) -> Optional[Any]:
        """Build the LLM client for the self-hosted Ollama server.

        Ollama is the only provider and needs no API key. The provider
        argument is accepted for call compatibility and ignored.
        """
        chosen_model = resolve_chat_model(model)
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=chosen_model,
                temperature=temperature,
                base_url=settings.OLLAMA_BASE_URL.rstrip("/"),
                keep_alive="30m",
                num_predict=512,
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatOllama: {e}")
            return None

    async def answer_question(self, question: str, history: List[Dict[str, str]] = None,
                              agent_config: Optional[Dict[str, Any]] = None,
                              agent_id: Optional[str] = None) -> ChatResponse:
        """Answer a question with RAG.

        agent_config (optional): {"name", "instructions", "language",
        "provider", "model", "temperature", "greeting"}.
        agent_id (optional): when given, retrieval searches ONLY that
        agent's own Chroma collection. When omitted, the legacy global
        collection is used (old /api/chat route).
        """
        agent_config = agent_config or {}
        provider = agent_config.get("provider")
        model = agent_config.get("model")
        temperature = float(agent_config.get("temperature", 0.1) or 0.1)
        temperature = min(0.3, max(0.0, temperature))
        language = agent_config.get("language") or "en"
        instructions = agent_config.get("instructions") or ""
        agent_name = agent_config.get("name") or "AI Assistant"

        show_citations = bool(agent_config.get("show_citations"))
        mode = agent_config.get("mode") or "rag"

        llm = self._get_llm(provider=provider, model=model, temperature=temperature)
        if not llm:
            msg = ("The self-hosted Ollama service is not available. "
                   "Please check that Ollama is running on the server and that the model "
                   f"'{settings.OLLAMA_MODEL}' is pulled (ollama pull {settings.OLLAMA_MODEL}), "
                   "then try again.")
            return ChatResponse(
                response=msg,
                sources=[],
                agent_steps=["Provider check failed."]
            )

        # Agent mode: hand over to the LangGraph tool-calling engine.
        if mode == "agent" and agent_id:
            try:
                from app.services.agent_engine import run_agent_answer
                return await run_agent_answer(
                    llm=llm, question=question, history=history,
                    agent_config=agent_config, agent_id=agent_id)
            except Exception:
                pass

        agent_steps = []

        # 1. Vector retrieval: tenant collection only when agent_id is set.
        # Retrieval is strictly scoped to this agent's own Chroma collection.
        try:
            agent_steps.append("Retrieving knowledge...")
            if agent_id:
                from app.services.tenant_vector_store import tenant_vector_store
                docs = tenant_vector_store.similarity_search(agent_id, question, k=settings.RETRIEVAL_K)
            else:
                docs = vector_store_service.similarity_search(question, k=settings.RETRIEVAL_K)
        except Exception as e:
            logger.error(f"[RAG] Knowledge retrieval failed for agent={agent_id}: {e}", exc_info=True)
            docs = []
            agent_steps.append("Knowledge search warning.")

        # Verify every returned chunk actually belongs to THIS agent (defence-in-depth).
        # If a chunk carries a different agent_id in metadata, discard it immediately.
        if docs and agent_id:
            before = len(docs)
            docs = [
                d for d in docs
                if not (d.metadata or {}).get("agent_id")
                or str((d.metadata or {}).get("agent_id")) == str(agent_id)
            ]
            discarded = before - len(docs)
            if discarded:
                logger.warning(
                    f"[RAG] Agent {agent_id}: discarded {discarded} chunk(s) with wrong agent_id"
                )

        logger.info(
            f"[RAG] Agent={agent_id or 'global'} | "
            f"query={question[:60]!r} | chunks_retrieved={len(docs)}"
        )

        context_parts = []
        sources: List[DocumentSource] = []
        if docs:
            seen_names = set()
            for doc in docs:
                content = (doc.page_content or "").strip()
                if content:
                    context_parts.append(content)
                if show_citations:
                    name = (doc.metadata or {}).get("document_name") or "Document"
                    if name not in seen_names:
                        seen_names.add(name)
                        sources.append(DocumentSource(
                            document_id=str((doc.metadata or {}).get("document_id") or ""),
                            document_name=name,
                            page=(doc.metadata or {}).get("page"),
                            snippet=content[:200],
                        ))

        # 2. Build prompt from the agent's own instructions and language.
        lang_note = f"Answer in {language}." if language else ""
        custom = f"\nAgent instructions: {instructions}" if instructions else ""
        if mode == "agent":
            custom += "\nYou may reason step by step over the knowledge before answering."
        if context_parts:
            context_text = "\n\n".join(context_parts)
            system_prompt = (
                f"You are {agent_name}, a knowledgeable, direct, and professional AI assistant. "
                "Your objective is to provide fast, highly accurate, and factual answers strictly grounded in the provided KNOWLEDGE.\n"
                f"{custom}\n"
                f"{lang_note}\n"
                "STRICT GROUNDING & ACCURACY RULES:\n"
                "1. Answer strictly using ONLY the facts explicitly stated in the KNOWLEDGE below. Do NOT assume, extrapolate, or invent any information.\n"
                "2. If the user's question cannot be completely answered from the provided KNOWLEDGE, politely state: 'I apologize, but I do not have that specific information in my knowledge base.' Never hallucinate or guess.\n"
                "3. Provide precise, specific details (such as names, numbers, dates, pricing, technical specifications, and steps) directly from the knowledge.\n"
                "4. Be concise, direct, and prompt. Avoid conversational filler, unnecessary apologies, or repeating the question.\n"
                "5. Never mention meta-terms such as 'according to the document', 'the provided text', 'source context', or 'uploaded file'. Answer authoritatively and naturally.\n"
                "6. Format with clean, readable structure (bullet points, clear paragraphs)."
            )
            user_prompt = f"KNOWLEDGE:\n{context_text}\n\nUSER QUESTION:\n{question}"
        else:
            system_prompt = (
                f"You are {agent_name}, a professional AI assistant.{custom}\n"
                f"{lang_note}\n"
                "No relevant knowledge is available for this question. Politely state: 'I apologize, but I do not have that specific information in my knowledge base.' Do not guess or hallucinate."
            )
            user_prompt = question

        messages = [SystemMessage(content=system_prompt)]

        if history:
            recent_history = history[-6:]
            for msg in recent_history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=user_prompt))

        # 3. Direct LLM invocation
        try:
            used_model = model or settings.get_active_model()
            agent_steps.append("Generating answer...")
            result = await llm.ainvoke(messages)

            output_text = ""
            if isinstance(result.content, str):
                output_text = result.content
            elif isinstance(result.content, list):
                parts = []
                for p in result.content:
                    if isinstance(p, dict) and p.get("text"):
                        parts.append(p["text"])
                    elif isinstance(p, str):
                        parts.append(p)
                output_text = "\n".join(parts) if parts else str(result.content)

            if not output_text.strip():
                output_text = "I do not have that information."

            if not agent_id:
                storage_service.increment_questions()
                storage_service.log_activity("chat", f"Asked: {question[:50]}...", "Answered")

            return ChatResponse(
                response=output_text.strip(),
                sources=sources if show_citations else [],
                agent_steps=[]
            )

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                friendly_msg = "AI provider rate limit/quota reached. Please wait a few seconds and try again."
            else:
                friendly_msg = f"Error generating answer: {error_str}"

            return ChatResponse(
                response=friendly_msg,
                sources=[],
                agent_steps=[]
            )

rag_agent_service = RAGAgentService()
