"""SQLAlchemy models and database session for the multi-tenant SaaS backend.

DATABASE_URL env: Postgres when set (postgresql+psycopg2), otherwise a local
SQLite file at ./data/app.db. Tables are created on startup (init_db).
"""
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "") or "sqlite:///./data/app.db"

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


def _new_id():
    return uuid.uuid4().hex


# Plan limits: messages per month, max agents, max documents, price USD/month.
PLANS = {
    "free": {
        "name": "Free",
        "price_usd": 0,
        "monthly_message_limit": 100,
        "agent_limit": 1,
        "document_limit": 5,
        "description": "Try one agent with a small knowledge base.",
    },
    "starter": {
        "name": "Starter",
        "price_usd": 19,
        "monthly_message_limit": 1000,
        "agent_limit": 5,
        "document_limit": 50,
        "description": "For small websites and small teams.",
    },
    "pro": {
        "name": "Pro",
        "price_usd": 49,
        "monthly_message_limit": 10000,
        "agent_limit": 20,
        "document_limit": 200,
        "description": "For growing businesses with more traffic.",
    },
    "scale": {
        "name": "Scale",
        "price_usd": 99,
        "monthly_message_limit": 50000,
        "agent_limit": 100,
        "document_limit": 1000,
        "description": "For high volume production use.",
    },
}


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=_new_id)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_super_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True, default=_new_id)
    owner_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    owner = relationship("User", back_populates="workspaces")
    agents = relationship("Agent", back_populates="workspace", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="workspace", uselist=False, cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(64), primary_key=True, default=_new_id)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)
    plan = Column(String(32), default="free", nullable=False)
    status = Column(String(32), default="active", nullable=False)
    monthly_message_limit = Column(Integer, default=PLANS["free"]["monthly_message_limit"], nullable=False)
    agent_limit = Column(Integer, default=PLANS["free"]["agent_limit"], nullable=False)
    document_limit = Column(Integer, default=PLANS["free"]["document_limit"], nullable=False)
    messages_used_this_month = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="subscription")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(64), primary_key=True, default=_new_id)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    instructions = Column(Text, default="", nullable=False)
    language = Column(String(32), default="en", nullable=False)
    provider = Column(String(32), default="gemini", nullable=False)
    model = Column(String(128), default="gemini-3.5-flash-lite", nullable=False)
    temperature = Column(Float, default=0.2, nullable=False)
    greeting = Column(Text, default="", nullable=False)
    description = Column(Text, default="", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    mode = Column(String(16), default="rag", nullable=False)
    show_citations = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="agents")
    documents = relationship("Document", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="agent", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, default=_new_id)
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    file_type = Column(String(32), nullable=False)
    file_size = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="processing", nullable=False)
    chunks_count = Column(Integer, default=0, nullable=False)
    source_type = Column(String(16), default="file", nullable=False)
    source_url = Column(String(1024), nullable=True)
    file_path = Column(String(1024), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    agent = relationship("Agent", back_populates="documents")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, default=_new_id)
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False, index=True)
    title = Column(String(512), default="", nullable=False)
    channel = Column(String(32), default="playground", nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(64), primary_key=True, default=_new_id)
    conversation_id = Column(String(64), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(Text, default="[]", nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True, default=_new_id)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    key_hash = Column(String(128), nullable=False, index=True)
    prefix = Column(String(32), nullable=False)
    name = Column(String(255), default="Default", nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    agent = relationship("Agent", back_populates="api_keys")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(String(64), primary_key=True, default=_new_id)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=True, index=True)
    kind = Column(String(32), nullable=False)
    tokens_or_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Create the data directory for the default SQLite file.
    if DATABASE_URL.startswith("sqlite"):
        path = DATABASE_URL.replace("sqlite:///", "")
        if path and path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate_agent_columns()


# Columns added to the agents table after the first release. Existing
# databases (SQLite or Postgres) do not gain them from create_all, so
# add any missing column with a safe server-side default.
_AGENT_COLUMN_DDL = {
    "description": "TEXT NOT NULL DEFAULT ''",
    "is_active": "BOOLEAN NOT NULL DEFAULT {true}",
    "mode": "VARCHAR(16) NOT NULL DEFAULT 'rag'",
    "show_citations": "BOOLEAN NOT NULL DEFAULT {false}",
}


def _migrate_agent_columns():
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "agents" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("agents")}
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        for name, ddl in _AGENT_COLUMN_DDL.items():
            if name in existing:
                continue
            rendered = ddl.format(true="1" if is_sqlite else "TRUE",
                                  false="0" if is_sqlite else "FALSE")
            conn.execute(text(f"ALTER TABLE agents ADD COLUMN {name} {rendered}"))


def ensure_free_subscription(db, workspace_id: str) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.workspace_id == workspace_id).first()
    if sub is None:
        sub = Subscription(workspace_id=workspace_id, plan="free", status="active")
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def apply_plan(subscription: Subscription, plan: str):
    plan_def = PLANS[plan]
    subscription.plan = plan
    subscription.monthly_message_limit = plan_def["monthly_message_limit"]
    subscription.agent_limit = plan_def["agent_limit"]
    subscription.document_limit = plan_def["document_limit"]
