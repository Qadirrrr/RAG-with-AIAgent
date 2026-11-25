import os
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.config import settings
from app.services.vector_store import vector_store_service
from app.services.storage import storage_service
from app.models.schemas import ChatResponse, DocumentSource

# Provider -> allowed chat models (validated again in routes/agents.py).
# For "ollama" the set holds known-good defaults, but any qwen* model
# string is also accepted (see is_model_allowed), because the exact tag
# installed on the self-hosted server is chosen by the operator.
ALLOWED_MODELS = {
    "gemini": {"gemini-3.5-flash-lite"},
    "openai": {"gpt-4o-mini", "gpt-4o"},
    "ollama": {"qwen2.5:7b", "qwen2.5:3b", "qwen2.5:14b", "qwen2.5:32b", "qwen3:8b"},
}


def is_model_allowed(provider: str, model: str) -> bool:
    if provider not in ALLOWED_MODELS:
        return False
    if provider == "ollama":
        return bool(model) and (model in ALLOWED_MODELS["ollama"] or model.startswith("qwen"))
    return model in ALLOWED_MODELS[provider]


class RAGAgentService:
    def __init__(self):
        pass

    def _get_llm(self, provider: Optional[str] = None, model: Optional[str] = None,
                 temperature: float = 0.2) -> Optional[Any]:
        """Build an LLM for the requested provider/model, or the active one."""
        if provider is None:
            provider = settings.get_active_provider()
        if provider == "gemini":
            key = settings.get_gemini_api_key()
            if not key:
                return None
            chosen_model = model if model in ALLOWED_MODELS["gemini"] else settings.GEMINI_MODEL
            return ChatGoogleGenerativeAI(
                model=chosen_model,
                google_api_key=key,
                temperature=temperature,
                max_retries=1  # Prevent long retry hangs
            )
        elif provider == "openai":
            key = settings.get_openai_api_key()
            if not key:
                return None
            chosen_model = model if model in ALLOWED_MODELS["openai"] else settings.OPENAI_MODEL
            return ChatOpenAI(
                model=chosen_model,
                temperature=temperature,
                openai_api_key=key,
                max_retries=1
            )
        elif provider == "ollama":
            # Self-hosted Ollama needs no cloud API key. Ollama exposes an
            # OpenAI-compatible endpoint at <base>/v1, so ChatOpenAI is
            # used with a dummy key instead of requiring langchain-ollama.
            chosen_model = model if is_model_allowed("ollama", model or "") else settings.OLLAMA_MODEL
            try:
                return ChatOpenAI(
                    model=chosen_model,
                    temperature=temperature,
                    openai_api_key="ollama",
                    base_url=settings.OLLAMA_BASE_URL.rstrip("/") + "/v1",
                    max_retries=1
                )
            except Exception:
                return None
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
            if provider == "ollama":
                msg = ("The self-hosted AI service (Ollama) is not available. "
                       "Please make sure Ollama is running on the server and try again.")
            else:
                msg = "AI API Key is not configured. Please add your `GEMINI_API_KEY` to `backend/.env`."
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
