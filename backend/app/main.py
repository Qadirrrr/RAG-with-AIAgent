import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.routes import documents, chat, health, stats, auth, workspaces, agents, knowledge, agent_chat, api_keys, analytics, admin, plans

# Create tables on import as well as on startup, so TestClient use
# without a lifespan context manager still has a working database.
init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for RAG AI Agent with LangChain, ChromaDB, and OpenAI."
)

# CORS: comma-separated origins from env, or * for local dev.
# Credentials are disabled when origins are * (browsers reject that combo).
cors_origins = [o.strip() for o in (settings.CORS_ORIGINS or "*").split(",") if o.strip()]
allow_all = cors_origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False if allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Legacy single-tenant routers (kept working as before)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(stats.router)

# Multi-tenant SaaS routers
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(agents.router)
app.include_router(knowledge.router)
app.include_router(agent_chat.tenant_router)
app.include_router(agent_chat.public_router)
app.include_router(api_keys.router)
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(plans.router)

# Alias for /health (in case clients query /health directly without /api prefix)
@app.get("/health", response_model=health.HealthResponse, tags=["health"])
async def root_health_check():
    return await health.health_check()

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
