"""POST /api/chat — single-agent RAG chat endpoint."""
import logging
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.rag_service import rag_service

logger = logging.getLogger("chat")
router = APIRouter(prefix="/api", tags=["chat"])


class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    history = [m.dict() for m in (req.history or [])]
    answer = await rag_service.answer(req.message, history)
    return ChatResponse(response=answer)
