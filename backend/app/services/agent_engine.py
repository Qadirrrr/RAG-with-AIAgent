"""LangGraph agent engine for chatbots in "agent" mode.

A ReAct agent (langgraph.prebuilt.create_react_agent) is built per
answer, bound ONLY with the tools in that chatbot's `tools_enabled`
allowlist. Every tool closes over the chatbot's own workspace_id and
agent_id, which are fixed at build time on the server; the model can
never pass or change them, so a tool can only ever touch its own
chatbot's knowledge and documents.

Safety: all tools are read-only (knowledge search, document list,
calculator, clock). There are no write or destructive tools, so no
approval flow is needed for sensitive actions. There is deliberately
no web, shell, file system or HTTP tool.

Failure behaviour: run_agent_answer raises on any error (including
graph recursion limits and timeouts) and the caller in
services/rag_agent.py falls back to the normal RAG answer path, so a
broken agent run never surfaces as a 500.
"""
import ast
import asyncio
import operator
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.config import settings
from app.models.schemas import ChatResponse, DocumentSource

ALL_TOOL_NAMES = ("knowledge_search", "list_documents", "calculator", "current_datetime")
DEFAULT_TOOLS_ENABLED = ",".join(ALL_TOOL_NAMES)

# Hard cap on one agent run, on top of the per-answer step limit.
AGENT_TIMEOUT_SECONDS = 120


def parse_tools_enabled(raw: Optional[str]) -> List[str]:
    """Parse the comma-separated allowlist stored on the chatbot.

    Unknown names are dropped; an empty or missing value means no
    tools (the agent then answers like a plain RAG chatbot).
    """
    if not raw:
        return []
    names = []
    for part in str(raw).split(","):
        name = part.strip()
        if name in ALL_TOOL_NAMES and name not in names:
            names.append(name)
    return names


# ---------------------------------------------------------------------------
# Safe calculator: AST walk over numbers and arithmetic operators only.
# Names, calls, attributes, subscripts and everything else are rejected,
# so expressions like __import__('os') or open('x') can never run.
# ---------------------------------------------------------------------------
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_POW_EXPONENT = 100  # keep ** from building gigantic numbers


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("Only numbers are allowed.")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POW_EXPONENT:
            raise ValueError("Exponent too large.")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Only numbers, + - * / % ** and parentheses are allowed.")


def calculate_expression(expression: str) -> str:
    """Evaluate a simple arithmetic expression, or return an error string."""
    try:
        tree = ast.parse(str(expression), mode="eval")
        result = _eval_node(tree)
    except Exception as e:
        return f"Error: could not calculate that expression. {e}"
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return str(result)


def _now_text() -> str:
    now_utc = datetime.now(timezone.utc)
    try:
        now_karachi = now_utc.astimezone(ZoneInfo("Asia/Karachi"))
        karachi_part = now_karachi.strftime("%Y-%m-%d %H:%M:%S Asia/Karachi (PKT)")
    except Exception:
        karachi_part = "unavailable"
    return f"Current date and time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} / {karachi_part}."


def build_tools(workspace_id: str, agent_id: str, show_citations: bool = False,
                tools_enabled: Optional[str] = None) -> Tuple[List, Dict[str, Any]]:
    """Build the allowlisted tools for ONE chatbot.

    workspace_id and agent_id are captured in the closures here, on the
    server, from the authenticated request's chatbot row. The model
    only supplies the tool arguments (a query, an expression), never
    the tenant ids.

    Returns (tools, state) where state collects citation sources from
    knowledge searches when show_citations is on.
    """
    state: Dict[str, Any] = {"sources": [], "_seen_sources": set()}

    def _record_sources(docs):
        if not show_citations:
            return
        for doc in docs:
            meta = doc.metadata or {}
            name = meta.get("document_name") or "Document"
            if name in state["_seen_sources"]:
                continue
            state["_seen_sources"].add(name)
            state["sources"].append(DocumentSource(
                document_id=str(meta.get("document_id") or ""),
                document_name=name,
                page=meta.get("page"),
                snippet=(doc.page_content or "")[:200],
            ))

    @tool
    def knowledge_search(query: str) -> str:
        """Search this chatbot's own uploaded knowledge for text relevant to the query. Use this before answering questions about the business, its documents, plans, prices or policies."""
        from app.services.tenant_vector_store import tenant_vector_store
        try:
            docs = tenant_vector_store.similarity_search(agent_id, query, k=settings.RETRIEVAL_K)
        except Exception:
            return "No knowledge was found for that query."
        if not docs:
            return "No knowledge was found for that query."
        _record_sources(docs)
        parts = []
        for doc in docs:
            text = (doc.page_content or "").strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts) if parts else "No information was found for that query."

    @tool
    def list_documents() -> str:
        """List the documents uploaded to this chatbot's knowledge base, with their processing status."""
        from app.db import Document, SessionLocal
        db = SessionLocal()
        try:
            rows = db.query(Document).filter(
                Document.agent_id == agent_id,
                Document.workspace_id == workspace_id,
            ).order_by(Document.created_at.asc()).all()
        finally:
            db.close()
        if not rows:
            return "This chatbot has no documents yet."
        return "\n".join(f"- {row.filename} (status: {row.status})" for row in rows)

    @tool
    def calculator(expression: str) -> str:
        """Calculate a simple arithmetic expression, for example '2 * (3 + 4)' or '19 * 12'. Only numbers and + - * / % ** with parentheses are supported."""
        return calculate_expression(expression)

    @tool
    def current_datetime() -> str:
        """Get the current date and time (UTC and Pakistan time)."""
        return _now_text()

    registry = {
        "knowledge_search": knowledge_search,
        "list_documents": list_documents,
        "calculator": calculator,
        "current_datetime": current_datetime,
    }
    allowed = parse_tools_enabled(
        tools_enabled if tools_enabled is not None else DEFAULT_TOOLS_ENABLED)
    return [registry[name] for name in allowed], state


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("text"):
                parts.append(p["text"])
            elif isinstance(p, str):
                parts.append(p)
        return "\n".join(parts)
    return str(content or "")


async def run_agent_answer(llm, question: str, history: Optional[List[Dict[str, str]]] = None,
                           agent_config: Optional[Dict[str, Any]] = None,
                           agent_id: Optional[str] = None) -> ChatResponse:
    """Run the LangGraph ReAct agent for one question.

    Raises on any failure (agent build, model, tools, recursion limit,
    timeout); the caller falls back to the plain RAG answer path.
    """
    from langgraph.prebuilt import create_react_agent

    agent_config = agent_config or {}
    workspace_id = agent_config.get("workspace_id") or ""
    show_citations = bool(agent_config.get("show_citations"))
    agent_name = agent_config.get("name") or "AI Assistant"
    language = agent_config.get("language") or "en"
    instructions = agent_config.get("instructions") or ""
    max_steps = max(1, int(getattr(settings, "AGENT_MAX_STEPS", 5) or 5))

    tools, state = build_tools(
        workspace_id=workspace_id,
        agent_id=agent_id or "",
        show_citations=show_citations,
        tools_enabled=agent_config.get("tools_enabled"),
    )

    if not tools:
        raise ValueError("No tools enabled for agent mode; falling back to RAG.")

    # Pre-fetch relevant RAG knowledge for this chatbot so the agent has
    # immediate grounded context on the first turn (faster + never misses
    # uploaded documents even if the LLM skips calling knowledge_search).
    pre_context = ""
    if agent_id:
        try:
            from app.services.tenant_vector_store import tenant_vector_store
            pre_docs = tenant_vector_store.similarity_search(agent_id, question, k=settings.RETRIEVAL_K)
            if pre_docs:
                parts = []
                seen_src = set()
                for d in pre_docs:
                    txt = (d.page_content or "").strip()
                    if txt:
                        parts.append(txt)
                    if show_citations:
                        meta = d.metadata or {}
                        name = meta.get("document_name") or "Document"
                        if name not in seen_src and name not in state["_seen_sources"]:
                            seen_src.add(name)
                            state["_seen_sources"].add(name)
                            state["sources"].append(DocumentSource(
                                document_id=str(meta.get("document_id") or ""),
                                document_name=name,
                                page=meta.get("page"),
                                snippet=txt[:200],
                            ))
                pre_context = "\n\n".join(parts)
        except Exception:
            pre_context = ""

    lang_note = f"Answer in {language}." if language else ""
    custom = f"\nChatbot instructions: {instructions}" if instructions else ""
    system_prompt = (
        f"You are {agent_name}, a professional and helpful assistant."
        f"{custom}\n"
        f"{lang_note}\n"
        "STRICT RULES (MUST FOLLOW):\n"
        "1. You must answer ONLY and EXCLUSIVELY using the Facts provided or retrieved from knowledge_search.\n"
        "2. If the question cannot be answered directly from the provided Facts, you MUST say: 'I do not have that information.' Do NOT attempt to answer using external or general knowledge.\n"
        "3. NEVER use pre-trained world knowledge, general facts, or assumptions outside the Facts.\n"
        "4. Include exact names, numbers, dates, and details from the Facts.\n"
        "5. Answer directly and professionally. NEVER say 'Based on', 'According to', 'From the provided knowledge', 'In the document', or mention 'facts/context/sources'. Start directly with the answer.\n"
        "6. Format cleanly with short paragraphs or bullet points."
    )

    graph = create_react_agent(model=llm, tools=tools, prompt=system_prompt)

    messages: List[Any] = []
    if history:
        for msg in history[-6:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
    if pre_context:
        messages.append(HumanMessage(content=f"Facts:\n{pre_context}\n\nQuestion:\n{question}"))
    else:
        messages.append(HumanMessage(content=question))

    # Each tool round trip costs about 2 graph steps, so the recursion
    # limit is derived from the configured max tool steps.
    result = await asyncio.wait_for(
        graph.ainvoke({"messages": messages},
                      config={"recursion_limit": max_steps * 2 + 3}),
        timeout=AGENT_TIMEOUT_SECONDS,
    )

    from app.services.rag_agent import clean_meta_prefix

    output_text = ""
    out_messages = result.get("messages") if isinstance(result, dict) else None
    if out_messages:
        output_text = _extract_text(out_messages[-1].content)
    output_text = clean_meta_prefix(output_text.strip())
    if not output_text:
        output_text = "I do not have that information."

    return ChatResponse(
        response=output_text,
        sources=state["sources"] if show_citations else [],
        agent_steps=[],
    )
