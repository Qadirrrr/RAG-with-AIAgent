from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class DocumentSource(BaseModel):
    document_id: str
    document_name: str
    page: Optional[int] = None
    snippet: str

class ChatMessage(BaseModel):
    role: str # "user" | "assistant" | "system"
    content: str
    sources: Optional[List[DocumentSource]] = None
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    response: str
    sources: List[DocumentSource] = []
    agent_steps: Optional[List[str]] = []

class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_date: datetime
    status: str # "processing" | "processed" | "failed"
    chunks_count: int = 0
    error_message: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentInfo

class DashboardStats(BaseModel):
    total_documents: int
    processed_documents: int
    total_chunks: int
    total_questions_asked: int
    recent_activity: List[Dict[str, Any]] = []

class HealthResponse(BaseModel):
    status: str
    provider: str # "gemini" | "openai" | "none"
    api_configured: bool
    openai_configured: bool
    chroma_status: str
    model: str
    embedding_model: str

