"""Tenant knowledge sources: file uploads and website URLs for one agent."""
import os
import re
import uuid
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from sqlalchemy.orm import Session

from app.config import settings
from app.db import Agent, Document, UsageEvent, ensure_free_subscription, get_db
from app.deps import get_current_user, get_workspace_or_404
from app.models.schemas import TenantDocumentOut, UrlIngestRequest
from app.services.document_loader import document_loader_service
from app.services.tenant_vector_store import tenant_vector_store

router = APIRouter(prefix="/api/workspaces", tags=["knowledge"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv"}
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_URL_CHARS = 200_000
MAX_SITEMAP_PAGES = 20


def _doc_out(d: Document) -> TenantDocumentOut:
    return TenantDocumentOut(id=d.id, agent_id=d.agent_id, workspace_id=d.workspace_id, filename=d.filename,
                             file_type=d.file_type, file_size=d.file_size, status=d.status,
                             chunks_count=d.chunks_count, source_type=d.source_type, source_url=d.source_url,
                             error_message=d.error_message, created_at=d.created_at)


def _get_agent(workspace_id: str, agent_id: str, user, db: Session) -> Agent:
    ws = get_workspace_or_404(workspace_id, user, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.workspace_id == ws.id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    return agent


def _check_document_limit(workspace_id: str, db: Session):
    sub = ensure_free_subscription(db, workspace_id)
    count = db.query(Document).filter(Document.workspace_id == workspace_id).count()
    if count >= sub.document_limit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Your {sub.plan} plan allows {sub.document_limit} document(s). Upgrade your plan to add more.")
    return sub


def _embed_chunks(agent, workspace_id: str, doc: Document, chunks, db: Session):
    """Embed chunks into the agent's private collection; mark failed on error."""
    try:
        n = tenant_vector_store.add_documents(agent.id, workspace_id, doc.id, chunks)
        doc.status = "processed"
        doc.chunks_count = n
        doc.error_message = None
        db.add(UsageEvent(workspace_id=workspace_id, agent_id=agent.id, kind="embedding", tokens_or_count=n))
    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    db.commit()
    db.refresh(doc)


@router.get("/{workspace_id}/agents/{agent_id}/documents", response_model=list[TenantDocumentOut])
def list_documents(workspace_id: str, agent_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    agent = _get_agent(workspace_id, agent_id, user, db)
    docs = db.query(Document).filter(Document.agent_id == agent.id).order_by(Document.created_at.desc()).all()
    return [_doc_out(d) for d in docs]


@router.post("/{workspace_id}/agents/{agent_id}/documents", response_model=TenantDocumentOut)
async def upload_document(workspace_id: str, agent_id: str, file: UploadFile = File(...),
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    agent = _get_agent(workspace_id, agent_id, user, db)
    _check_document_limit(workspace_id, db)
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unsupported file type '{ext}'. Allowed types: PDF, DOCX, TXT, MD, CSV.")
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too large. Maximum size is 10 MB.")

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    doc_id = uuid.uuid4().hex
    upload_dir = os.path.join(settings.UPLOAD_DIRECTORY, workspace_id, agent.id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{doc_id}_{safe_name}")
    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(id=doc_id, agent_id=agent.id, workspace_id=workspace_id, filename=filename,
                   file_type=ext.replace(".", "").upper(), file_size=len(content), status="processing",
                   chunks_count=0, source_type="file", file_path=file_path)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.add(UsageEvent(workspace_id=workspace_id, agent_id=agent.id, kind="upload", tokens_or_count=1))
    db.commit()

    try:
        chunks = document_loader_service.load_and_split(file_path, doc.id, filename)
    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read document: {e}")
    _embed_chunks(agent, workspace_id, doc, chunks, db)
    return _doc_out(doc)


def _fetch_text(url: str) -> str:
    """Fetch a web page and return its readable text, capped per page."""
    resp = httpx.get(url, timeout=20, follow_redirects=True,
                     headers={"User-Agent": "RAG-AI-Agent/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:MAX_URL_CHARS]


def _ingest_page(agent, workspace_id: str, page_url: str, text: str, db: Session) -> Document:
    filename = page_url.replace("https://", "").replace("http://", "").rstrip("/") or "website"
    doc = Document(agent_id=agent.id, workspace_id=workspace_id, filename=filename, file_type="URL",
                   file_size=len(text.encode("utf-8")), status="processing", chunks_count=0,
                   source_type="url", source_url=page_url)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    chunks = document_loader_service.split_text(text, doc.id, filename, {"source_url": page_url})
    _embed_chunks(agent, workspace_id, doc, chunks, db)
    return doc


def _parse_sitemap_urls(xml_text: str) -> list:
    soup = BeautifulSoup(xml_text, "xml")
    return [loc.get_text(strip=True) for loc in soup.find_all("loc") if loc.get_text(strip=True)]


@router.post("/{workspace_id}/agents/{agent_id}/documents/url", response_model=TenantDocumentOut)
def ingest_url(workspace_id: str, agent_id: str, payload: UrlIngestRequest,
               user=Depends(get_current_user), db: Session = Depends(get_db)):
    agent = _get_agent(workspace_id, agent_id, user, db)
    _check_document_limit(workspace_id, db)
    url = payload.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL must start with http:// or https://")

    is_sitemap = (payload.type or "").lower() == "sitemap" or url.rstrip("/").endswith("sitemap.xml")
    if is_sitemap:
        try:
            resp = httpx.get(url, timeout=20, follow_redirects=True,
                             headers={"User-Agent": "RAG-AI-Agent/1.0"})
            resp.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not fetch sitemap: {e}")
        page_urls = _parse_sitemap_urls(resp.text)[:MAX_SITEMAP_PAGES]
        if not page_urls:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No page URLs found in that sitemap.")
        first_doc = None
        ingested = 0
        for page_url in page_urls:
            try:
                text = _fetch_text(page_url)
            except Exception:
                continue
            if len(text) < 50:
                continue
            doc = _ingest_page(agent, workspace_id, page_url, text, db)
            if first_doc is None:
                first_doc = doc
            ingested += 1
        if first_doc is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="None of the sitemap pages had readable text.")
        return _doc_out(first_doc)

    try:
        text = _fetch_text(url)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not fetch URL: {e}")
    if len(text) < 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No readable text found on that page.")
    doc = _ingest_page(agent, workspace_id, url, text, db)
    return _doc_out(doc)


@router.delete("/{workspace_id}/agents/{agent_id}/documents/{document_id}")
def delete_document(workspace_id: str, agent_id: str, document_id: str,
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    agent = _get_agent(workspace_id, agent_id, user, db)
    doc = db.query(Document).filter(Document.id == document_id, Document.agent_id == agent.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    tenant_vector_store.delete_document(agent.id, document_id)
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully", "id": document_id}
