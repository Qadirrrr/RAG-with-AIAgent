import os
import time
from typing import List, Dict, Any, Optional, Set

import httpx
# The chat model client (ChatOllama from langchain_ollama) is imported
# lazily inside _get_llm: Ollama is the only AI provider in this
# platform, and there are no cloud providers to fall back to.
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.config import settings
from app.services.vector_store import vector_store_service
from app.services.storage import storage_service
from app.models.schemas import ChatResponse, DocumentSource

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
            )
        except Exception:
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
        temperature = float(agent_config.get("temperature", 0.2) or 0.2)
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
        # Any failure (tool error, recursion limit, timeout) falls back
        # to the standard RAG path below instead of surfacing an error.
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
        try:
            agent_steps.append("Retrieving knowledge...")
            if agent_id:
                from app.services.tenant_vector_store import tenant_vector_store
                docs = tenant_vector_store.similarity_search(agent_id, question, k=4)
            else:
                docs = vector_store_service.similarity_search(question, k=4)
        except Exception as e:
            docs = []
            agent_steps.append("Knowledge search warning.")

        context_parts = []
        sources: List[DocumentSource] = []
        if docs:
            seen_names = set()
            for doc in docs:
                content = doc.page_content.strip()
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
            # Fallback path only: agent mode normally runs the LangGraph
            # tool engine above. If that run failed, answer from the
            # retrieved knowledge with careful multi-step reasoning.
            custom += "\nYou may reason step by step over the knowledge before answering."
        if context_parts:
            context_text = "\n\n".join(context_parts)
            system_prompt = (
                f"You are {agent_name}, a professional support assistant. Answer the question directly and professionally, using only the knowledge provided below."
                f"{custom}\n"
                f"{lang_note}\n"
                "Rules:\n"
                "1. Give a concise, accurate, direct answer using only the knowledge below. Do not add anything that is not in the knowledge.\n"
                "2. Never mention documents, files, pages, sources, citations, or where an answer came from. Never write phrases such as according to, as stated in, the document says, or from the source.\n"
                "3. If the knowledge below does not cover the question, say politely: 'I do not have that information.' Do not guess or invent an answer.\n"
                "4. Use a professional tone and avoid unnecessary filler words.\n"
                "5. Format the answer cleanly with short paragraphs and simple bullet points. Do not use asterisks, hashes, underscores, or em dashes for formatting."
            )
            user_prompt = f"KNOWLEDGE:\n{context_text}\n\nUSER QUESTION:\n{question}"
        else:
            system_prompt = (
                f"You are {agent_name}, a professional support assistant.{custom}\n"
                f"{lang_note}\n"
                "No relevant knowledge is available for this question. Politely say: 'I do not have that information.' Do not guess or invent an answer."
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
