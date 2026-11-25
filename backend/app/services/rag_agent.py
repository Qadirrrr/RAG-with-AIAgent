import os
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.config import settings
from app.services.vector_store import vector_store_service
from app.services.storage import storage_service
from app.models.schemas import DocumentSource, ChatResponse

# Provider -> allowed chat models (validated again in routes/agents.py).
ALLOWED_MODELS = {
    "gemini": {"gemini-2.0-flash", "gemini-3.5-flash-lite"},
    "openai": {"gpt-4o-mini", "gpt-4o"},
}


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

        llm = self._get_llm(provider=provider, model=model, temperature=temperature)
        if not llm:
            return ChatResponse(
                response="AI API Key is not configured. Please add your `GEMINI_API_KEY` to `backend/.env`.",
                sources=[],
                agent_steps=["API Key check failed."]
            )

        agent_steps = []
        sources: List[DocumentSource] = []

        # 1. Vector retrieval: tenant collection only when agent_id is set.
        try:
            agent_steps.append("Retrieving semantic vector context from ChromaDB...")
            if agent_id:
                from app.services.tenant_vector_store import tenant_vector_store
                docs = tenant_vector_store.similarity_search(agent_id, question, k=4)
            else:
                docs = vector_store_service.similarity_search(question, k=4)
        except Exception as e:
            docs = []
            agent_steps.append(f"Vector search warning: {str(e)}")

        context_parts = []
        if docs:
            for doc in docs:
                doc_id = doc.metadata.get("document_id", "unknown")
                doc_name = doc.metadata.get("document_name", "Untitled")
                page = doc.metadata.get("page", 1)
                content = doc.page_content.strip()

                if not any(s.document_id == doc_id and s.snippet == content[:300] for s in sources):
                    sources.append(
                        DocumentSource(
                            document_id=doc_id,
                            document_name=doc_name,
                            page=page,
                            snippet=content[:300] + ("..." if len(content) > 300 else "")
                        )
                    )

                context_parts.append(
                    f"--- Source Document: {doc_name} (Page {page}) ---\n{content}"
                )

        # 2. Build prompt from the agent's own instructions and language.
        lang_note = f"Answer in {language}." if language else ""
        custom = f"\nAgent instructions: {instructions}" if instructions else ""
        if context_parts:
            context_text = "\n\n".join(context_parts)
            system_prompt = (
                f"You are {agent_name}, an expert AI Knowledge Assistant answering questions strictly based on the provided document context."
                f"{custom}\n"
                f"{lang_note}\n"
                "Rules:\n"
                "1. Synthesize a concise, accurate, and direct response strictly using the context below.\n"
                "2. Reference the document name and page number if relevant.\n"
                "3. If the provided context does not contain enough information to answer the question, clearly state: "
                "'I could not find relevant information in the uploaded documents to answer your question.'\n"
                "4. Be direct, professional, and avoid unnecessary filler words."
            )
            user_prompt = f"DOCUMENT CONTEXT:\n{context_text}\n\nUSER QUESTION:\n{question}"
        else:
            system_prompt = (
                f"You are {agent_name}, an AI Knowledge Assistant.{custom}\n"
                f"{lang_note}\n"
                "The user has not yet uploaded relevant knowledge documents or no matching content was found.\n"
                "Politely inform the user that no relevant documents were found and encourage them to upload documents for this agent."
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
            agent_steps.append(f"Generating answer using {used_model}...")
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
                output_text = "I could not find relevant information in the uploaded documents to answer your question."

            if not agent_id:
                storage_service.increment_questions()
                storage_service.log_activity("chat", f"Asked: {question[:50]}...", f"Answered with {len(sources)} source(s)")

            return ChatResponse(
                response=output_text.strip(),
                sources=sources,
                agent_steps=agent_steps
            )

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                friendly_msg = "AI provider rate limit/quota reached. Please wait a few seconds and try again."
            else:
                friendly_msg = f"Error generating answer: {error_str}"

            return ChatResponse(
                response=friendly_msg,
                sources=sources,
                agent_steps=[f"Error: {error_str}"]
            )

rag_agent_service = RAGAgentService()
