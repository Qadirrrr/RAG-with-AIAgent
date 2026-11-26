"""Simplified RAG Chatbot Backend — single agent, no auth, no DB."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import chat, documents, health

app = FastAPI(title="RAG Chatbot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(documents.router)

@app.get("/")
def root():
    return {"message": "RAG Chatbot API is running", "docs": "/docs"}
