"""Agent document diagnostics — authenticated debug endpoint.

GET  /api/workspaces/{workspace_id}/agents/{agent_id}/debug/chunks
     Returns how many vector chunks this agent has stored and a list of
     all document names with their chunk counts.

POST /api/workspaces/{workspace_id}/agents/{agent_id}/debug/search
     Body: {"query": "...", "k": 5}
     Returns the top-k retrieved chunks WITH relevance scores so you can
     see exactly what the chatbot sees when it answers a question.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import Agent, Document, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.services.tenant_vector_store import tenant_vector_store
import chromadb
from app.config import settings
import re

router = APIRouter(prefix="/api/workspaces", tags=["debug"])


def _get_agent(workspace_id: str, agent_id: str, user, db: Session) -> Agent:
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.workspace_id == ws.id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    return agent


class SearchDebugRequest(BaseModel):
    query: str
    k: int = 5


@router.get("/{workspace_id}/agents/{agent_id}/debug/chunks")
def debug_chunks(workspace_id: str, agent_id: str,
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Show exactly how many chunks this chatbot has stored in its vector collection,
    broken down by document. Use this to verify that documents were ingested correctly.
    """
    agent = _get_agent(workspace_id, agent_id, user, db)

    # DB-level document list
    db_docs = db.query(Document).filter(
        Document.agent_id == agent.id,
        Document.workspace_id == workspace_id,
    ).order_by(Document.created_at.desc()).all()

    db_summary = [
        {
            "document_id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "status": d.status,
            "chunks_count_db": d.chunks_count,
            "source_type": d.source_type,
            "source_url": d.source_url,
            "error_message": d.error_message,
        }
        for d in db_docs
    ]

    # Vector-level chunk count (actual stored in Chroma)
    total_vector_chunks = tenant_vector_store.count_chunks(agent.id)

    collection_name = f"agent_{re.sub(r'[^a-zA-Z0-9_-]', '_', str(agent.id))}"[:120]

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "collection_name": collection_name,
        "total_vector_chunks": total_vector_chunks,
        "total_db_documents": len(db_docs),
        "documents": db_summary,
        "hint": (
            "If chunks_count_db > 0 but total_vector_chunks is 0, "
            "the document was recorded in the DB but embedding failed. "
            "Delete and re-upload the document while Ollama is running."
        ),
    }


@router.post("/{workspace_id}/agents/{agent_id}/debug/search")
def debug_search(workspace_id: str, agent_id: str, payload: SearchDebugRequest,
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Run a retrieval search for a query and show the exact chunks the chatbot
    would see — with relevance scores. Use this to verify accuracy before
    testing the chatbot in the playground.

    Score interpretation (BGE embeddings, cosine similarity):
      >= 0.70  → Very strong match — answer is almost certainly here
      0.50-0.69 → Good match — likely relevant
      0.30-0.49 → Moderate match — may be relevant
      < 0.30   → Weak match — probably not related to this question
    """
    agent = _get_agent(workspace_id, agent_id, user, db)
    k = max(1, min(payload.k, 20))

    results = tenant_vector_store.search_with_scores(agent.id, payload.query, k=k)

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "query": payload.query,
        "k": k,
        "results_count": len(results),
        "relevance_threshold": 0.30,
        "results": results,
        "interpretation": {
            ">=0.70": "Very strong match",
            "0.50-0.69": "Good match",
            "0.30-0.49": "Moderate match",
            "<0.30": "Weak / likely irrelevant",
        },
    }
