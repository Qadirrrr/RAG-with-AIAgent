import os
from typing import List, Dict, Any, Tuple, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from app.config import settings
from app.services.vector_store import vector_store_service
from app.services.storage import storage_service
from app.models.schemas import DocumentSource, ChatResponse

class SourceTracker:
    def __init__(self):
        self.sources: List[DocumentSource] = []

    def add_source(self, source: DocumentSource):
        if not any(s.document_id == source.document_id and s.snippet == source.snippet for s in self.sources):
            self.sources.append(source)

    def clear(self):
        self.sources.clear()

source_tracker = SourceTracker()

@tool
def search_documents(query: str) -> str:
    """Searches the uploaded documents for semantic information relevant to the user's query."""
    docs = vector_store_service.similarity_search(query, k=5)
    if not docs:
        return "No relevant documents found in the database."

    results = []
    for doc in docs:
        doc_id = doc.metadata.get("document_id", "unknown")
        doc_name = doc.metadata.get("document_name", "Untitled")
        page = doc.metadata.get("page", 1)
        content = doc.page_content.strip()
        
        source_tracker.add_source(
            DocumentSource(
                document_id=doc_id,
                document_name=doc_name,
                page=page,
                snippet=content[:300] + ("..." if len(content) > 300 else "")
            )
        )
        
        results.append(
            f"--- Document: {doc_name} (Page {page}) ---\n{content}\n"
        )

    return "\n".join(results)

class RAGAgentService:
    def __init__(self):
        self.tools = [search_documents]

    def _get_llm(self) -> Optional[Any]:
        provider = settings.get_active_provider()
        if provider == "gemini":
            key = settings.get_gemini_api_key()
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                temperature=0.2,
                google_api_key=key
            )
        elif provider == "openai":
            key = settings.get_openai_api_key()
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0.2,
                openai_api_key=key
            )
        return None

    async def answer_question(self, question: str, history: List[Dict[str, str]] = None) -> ChatResponse:
        llm = self._get_llm()
        if not llm:
            return ChatResponse(
                response="AI API Key is not configured. Please add your `GEMINI_API_KEY` (or `OPENAI_API_KEY`) to `backend/.env` to enable AI answers.",
                sources=[],
                agent_steps=["API Key check failed."]
            )

        source_tracker.clear()
        agent_steps = []

        system_prompt = (
            "You are a Senior AI Assistant and Knowledge Agent with access to the user's uploaded documents.\n"
            "Your goal is to provide accurate, concise, and helpful answers strictly based on the documents.\n\n"
            "Rules:\n"
            "1. ALWAYS call the `search_documents` tool to query the document store before answering.\n"
            "2. If the retrieved documents contain the answer, synthesize the answer clearly and reference the source document names and page numbers.\n"
            "3. If the retrieved documents DO NOT contain sufficient information or no relevant documents are found, explicitly tell the user: "
            "'I could not find relevant information in the uploaded documents to answer your question.'\n"
            "4. Do NOT hallucinate facts or provide information outside of the retrieved context unless asked for general formatting or clarification.\n"
            "5. Maintain a professional, polite, and helpful tone."
        )

        agent = create_react_agent(
            model=llm,
            tools=self.tools,
            prompt=system_prompt
        )

        messages = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))
        messages.append(HumanMessage(content=question))

        try:
            result = await agent.ainvoke({"messages": messages})
            
            output_messages = result.get("messages", [])
            output_text = ""
            for m in reversed(output_messages):
                if isinstance(m, AIMessage) and m.content:
                    if isinstance(m.content, str):
                        output_text = m.content
                        break
                    elif isinstance(m.content, list):
                        parts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in m.content]
                        output_text = "\n".join(parts)
                        break

            for m in output_messages:
                if isinstance(m, ToolMessage):
                    agent_steps.append(f"Tool {m.name} executed: {m.content[:100]}...")

            if not output_text:
                output_text = "I could not find relevant information in the uploaded documents to answer your question."

            storage_service.increment_questions()
            storage_service.log_activity("chat", f"Asked: {question[:50]}...", f"Generated response using {len(source_tracker.sources)} source(s)")

            return ChatResponse(
                response=output_text,
                sources=list(source_tracker.sources),
                agent_steps=agent_steps
            )

        except Exception as e:
            error_msg = str(e)
            return ChatResponse(
                response=f"An error occurred while generating the response: {error_msg}",
                sources=[],
                agent_steps=[f"Error: {error_msg}"]
            )

rag_agent_service = RAGAgentService()
