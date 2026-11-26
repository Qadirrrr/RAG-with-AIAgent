"""Document upload / list / delete — feeds the RAG vector store.
No DB required — persists metadata to a simple JSON registry file.
"""
import json
import logging
import os
import uuid
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger("documents")
router = APIRouter(prefix="/api/documents", tags=["documents"])

REGISTRY_FILE = os.path.join(settings.UPLOAD_DIRECTORY, "documents_registry.json")


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    chunks: int


def _load_registry() -> dict:
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not read registry file: {e}")
    return {}


def _save_registry(data: dict):
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Could not save registry file: {e}")


@router.get("", response_model=List[DocumentOut])
def list_documents():
    reg = _load_registry()
    return [
        DocumentOut(id=k, filename=v.get("filename", ""), status=v.get("status", "processed"), chunks=v.get("chunks", 0))
        for k, v in reg.items()
    ]


@router.post("", response_model=DocumentOut)
async def upload_document(file: UploadFile = File(...)):
    allowed = {".pdf", ".txt", ".docx", ".csv", ".md"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}")

    doc_id = uuid.uuid4().hex
    save_path = os.path.join(settings.UPLOAD_DIRECTORY, f"{doc_id}{ext}")

    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    reg = _load_registry()
    reg[doc_id] = {"filename": file.filename, "status": "processing", "chunks": 0}
    _save_registry(reg)

    try:
        chunks = rag_service.ingest_file(save_path, doc_id, file.filename)
        reg[doc_id]["status"] = "processed"
        reg[doc_id]["chunks"] = chunks
        _save_registry(reg)
        logger.info(f"Ingested {file.filename} → {chunks} chunks (id={doc_id})")
    except Exception as e:
        reg[doc_id]["status"] = "error"
        _save_registry(reg)
        logger.error(f"Ingest failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")

    return DocumentOut(
        id=doc_id,
        filename=file.filename,
        status=reg[doc_id]["status"],
        chunks=reg[doc_id]["chunks"],
    )


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    reg = _load_registry()
    if doc_id not in reg:
        raise HTTPException(status_code=404, detail="Document not found")

    info = reg.pop(doc_id)
    _save_registry(reg)

    # Remove from vector store
    try:
        rag_service.delete_document(doc_id)
    except Exception as e:
        logger.warning(f"Vector store delete failed for {doc_id}: {e}")

    # Remove uploaded file
    for ext in (".pdf", ".txt", ".docx", ".csv", ".md"):
        path = os.path.join(settings.UPLOAD_DIRECTORY, f"{doc_id}{ext}")
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
            break

    return {"deleted": True, "filename": info.get("filename", "")}
