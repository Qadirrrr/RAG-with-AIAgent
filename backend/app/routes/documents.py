import os
import uuid
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.config import settings
from app.models.schemas import DocumentInfo, DocumentUploadResponse, DashboardStats
from app.services.storage import storage_service
from app.services.document_loader import document_loader_service
from app.services.vector_store import vector_store_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: PDF, DOCX, TXT."
        )

    doc_id = uuid.uuid4().hex[:12]
    timestamp = datetime.utcnow()
    
    # Save file to upload directory
    safe_filename = f"{doc_id}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIRECTORY, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Initial metadata
    doc_info = {
        "id": doc_id,
        "filename": filename,
        "file_type": ext.replace(".", "").upper(),
        "file_size": file_size,
        "upload_date": timestamp.isoformat(),
        "status": "processing",
        "chunks_count": 0,
        "error_message": None,
        "file_path": file_path
    }
    storage_service.save_document(doc_info)

    # Extract, chunk, and embed
    try:
        chunks = document_loader_service.load_and_split(file_path, doc_id, filename)
        
        # Check provider & embeddings
        provider = settings.get_active_provider()
        if provider == "none":
            doc_info["status"] = "failed"
            doc_info["error_message"] = "AI API Key is missing. Configure GEMINI_API_KEY (or OPENAI_API_KEY) in backend/.env to generate embeddings."
            storage_service.save_document(doc_info)
            storage_service.log_activity("upload_failed", f"Failed: {filename}", "AI API Key missing")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI API Key is not configured. Please add GEMINI_API_KEY to backend/.env."
            )

        vector_store_service.add_documents(chunks)
        
        # Mark as processed
        doc_info["status"] = "processed"
        doc_info["chunks_count"] = len(chunks)
        doc_info["error_message"] = None
        storage_service.save_document(doc_info)
        storage_service.log_activity("upload", f"Uploaded: {filename}", f"Generated {len(chunks)} chunks")

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "no credits remaining" in error_str.lower() or "insufficient_quota" in error_str.lower():
            friendly_error = "OpenAI Quota Exceeded (429): You have no credits remaining on your OpenAI account. Please add billing credits at https://platform.openai.com/settings/organization/billing or provide an active API key."
        elif "invalid_api_key" in error_str.lower() or "incorrect api key" in error_str.lower():
            friendly_error = "Invalid OpenAI API Key. Please verify the OPENAI_API_KEY in backend/.env."
        else:
            friendly_error = f"Failed to process and embed document: {error_str}"

        doc_info["status"] = "failed"
        doc_info["error_message"] = friendly_error
        storage_service.save_document(doc_info)
        storage_service.log_activity("upload_failed", f"Failed: {filename}", friendly_error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=friendly_error
        )

    return DocumentUploadResponse(
        message="Document uploaded and processed successfully",
        document=DocumentInfo(
            id=doc_info["id"],
            filename=doc_info["filename"],
            file_type=doc_info["file_type"],
            file_size=doc_info["file_size"],
            upload_date=timestamp,
            status=doc_info["status"],
            chunks_count=doc_info["chunks_count"],
            error_message=doc_info["error_message"]
        )
    )

@router.get("", response_model=list[DocumentInfo])
async def list_documents():
    docs = storage_service.get_all_documents()
    result = []
    for d in docs:
        result.append(
            DocumentInfo(
                id=d["id"],
                filename=d["filename"],
                file_type=d["file_type"],
                file_size=d["file_size"],
                upload_date=datetime.fromisoformat(d["upload_date"]) if isinstance(d["upload_date"], str) else d["upload_date"],
                status=d["status"],
                chunks_count=d.get("chunks_count", 0),
                error_message=d.get("error_message")
            )
        )
    return result

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    doc = storage_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Remove from Chroma
    vector_store_service.delete_document(document_id)

    # Remove physical file
    file_path = doc.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    # Remove from storage
    storage_service.delete_document(document_id)
    storage_service.log_activity("delete", f"Deleted: {doc.get('filename')}", f"Removed ID: {document_id}")

    return {"message": "Document deleted successfully", "id": document_id}

