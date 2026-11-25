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
    provider: str # always "ollama" (the only, self-hosted provider)
    ollama_reachable: bool
    api_configured: bool # kept for older clients: same as ollama_reachable
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
    provider: str = "ollama"
    model: str = "qwen2.5:7b"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    greeting: str = ""
    description: str = ""
    is_active: bool = True
    mode: str = "rag"
    show_citations: bool = False
    tools_enabled: str = "knowledge_search,list_documents,calculator,current_datetime"
    widget_title: str = ""
    widget_welcome_message: str = "Hello! How can I help you?"
    widget_color: str = "#0F766E"
    widget_position: str = "right"
    widget_icon: str = "chat"
    widget_icon_url: str = ""


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    instructions: Optional[str] = None
    language: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    greeting: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    mode: Optional[str] = None
    show_citations: Optional[bool] = None
    tools_enabled: Optional[str] = None
    widget_title: Optional[str] = None
    widget_welcome_message: Optional[str] = None
    widget_color: Optional[str] = None
    widget_position: Optional[str] = None
    widget_icon: Optional[str] = None
    widget_icon_url: Optional[str] = None


class AgentOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    instructions: str = ""
    language: str = "en"
    provider: str = "ollama"
    model: str = "qwen2.5:7b"
    temperature: float = 0.2
    greeting: str = ""
    description: str = ""
    is_active: bool = True
    mode: str = "rag"
    show_citations: bool = False
    tools_enabled: str = "knowledge_search,list_documents,calculator,current_datetime"
    widget_title: str = ""
    widget_welcome_message: str = "Hello! How can I help you?"
    widget_color: str = "#0F766E"
    widget_position: str = "right"
    widget_icon: str = "chat"
    widget_icon_url: str = ""
    created_at: Optional[datetime] = None


class WidgetConfigOut(BaseModel):
    """Public appearance config for the embeddable website widget.

    Returned by GET /api/public/widget-config. Contains appearance only:
    no instructions, documents or other agent internals.
    """
    title: str
    welcome_message: str
    color: str
    position: str
    icon: str
    icon_url: str = ""
    agent_name: str


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
    # "url" for a single page (default), "sitemap" to crawl a sitemap.xml
    type: Optional[str] = None


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


