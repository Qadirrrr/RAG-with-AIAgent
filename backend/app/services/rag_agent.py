import os
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.config import settings
from app.services.vector_store import vector_store_service
from app.services.storage import storage_service
from app.models.schemas import DocumentSource, ChatResponse

class RAGAgentService:
    def __init__(self):
        pass

    def _get_llm(self) -> Optional[Any]:
        provider = settings.get_active_provider()
        if provider == "gemini":
            key = settings.get_gemini_api_key()
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=key,
                max_retries=1  # Prevent long retry hangs
            )
        elif provider == "openai":
            key = settings.get_openai_api_key()
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0.2,
                openai_api_key=key,
                max_retries=1
            )
        return None

    async def answer_question(self, question: str, history: List[Dict[str, str]] = None) -> ChatResponse:
        llm = self._get_llm()
        if not llm:
            return ChatResponse(
                response="AI API Key is not configured. Please add your `GEMINI_API_KEY` to `backend/.env`.",
                sources=[],
                agent_steps=["API Key check failed."]
            )

        agent_steps = []
        sources: List[DocumentSource] = []

        # 1. Fast Vector Retrieval directly from ChromaDB (< 20ms)
        try:
            agent_steps.append("Retrieving semantic vector context from ChromaDB...")
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

        # 2. Build Fast Single-Turn Prompt
        if context_parts:
            context_text = "\n\n".join(context_parts)
            system_prompt = (
                "You are an expert AI Knowledge Assistant answering questions strictly based on the provided document context.\n"
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
                "You are an AI Knowledge Assistant. The user has not yet uploaded relevant knowledge documents or no matching content was found in ChromaDB.\n"
                "Politely inform the user that no relevant documents were found and encourage them to upload documents in the Documents tab."
            )
            user_prompt = question

        # Build message list
        messages = [SystemMessage(content=system_prompt)]
        
        # Include last 3 conversation turns for speed & context
        if history:
            recent_history = history[-6:]
            for msg in recent_history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=user_prompt))

        # 3. Direct Fast LLM Invocation (< 1.5 seconds)
        try:
            agent_steps.append(f"Generating answer using {settings.GEMINI_MODEL}...")
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
                friendly_msg = "Google Gemini rate limit/quota reached for this minute. Please wait a few seconds and try again."
            else:
                friendly_msg = f"Error generating answer: {error_str}"

            return ChatResponse(
                response=friendly_msg,
                sources=sources,
                agent_steps=[f"Error: {error_str}"]
            )

rag_agent_service = RAGAgentService()
