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


# ---- SaaS schemas ----

class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    is_super_admin: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceOut(BaseModel):
    id: str
    owner_id: str
    name: str
    created_at: Optional[datetime] = None


class SubscriptionOut(BaseModel):
    id: str
    workspace_id: str
    plan: str
    status: str
    monthly_message_limit: int
    agent_limit: int
    document_limit: int
    messages_used_this_month: int


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    instructions: str = ""
    language: str = "en"
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    greeting: str = ""


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    instructions: Optional[str] = None
    language: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    greeting: Optional[str] = None


class AgentOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    instructions: str = ""
    language: str = "en"
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    temperature: float = 0.2
    greeting: str = ""
    created_at: Optional[datetime] = None


class TenantDocumentOut(BaseModel):
    id: str
    agent_id: str
    workspace_id: str
    filename: str
    file_type: str
    file_size: int = 0
    status: str
    chunks_count: int = 0
    source_type: str = "file"
    source_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class UrlIngestRequest(BaseModel):
    url: str


class TenantChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    channel: str = "playground"


class TenantChatResponse(BaseModel):
    conversation_id: str
    response: str
    sources: List[DocumentSource] = []
    agent_steps: Optional[List[str]] = []


class PublicChatRequest(BaseModel):
    agent_id: str
    message: str
    conversation_id: Optional[str] = None
    channel: str = "widget"


class ApiKeyCreate(BaseModel):
    name: str = "Default"


class ApiKeyOut(BaseModel):
    id: str
    workspace_id: str
    agent_id: str
    prefix: str
    name: str
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class ApiKeyCreatedOut(ApiKeyOut):
    api_key: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: List[DocumentSource] = []
    created_at: Optional[datetime] = None


class ConversationOut(BaseModel):
    id: str
    agent_id: str
    workspace_id: str
    title: str
    channel: str
    created_at: Optional[datetime] = None
    messages: List[MessageOut] = []


class PlanOut(BaseModel):
    id: str
    name: str
    price_usd: int
    monthly_message_limit: int
    agent_limit: int
    document_limit: int
    description: str


class SubscriptionChangeRequest(BaseModel):
    plan: str


class AdminUserUpdate(BaseModel):
    is_super_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class AdminSubscriptionUpdate(BaseModel):
    plan: Optional[str] = None
    status: Optional[str] = None
    monthly_message_limit: Optional[int] = None
    agent_limit: Optional[int] = None
    document_limit: Optional[int] = None


