from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_agent import rag_agent_service

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    history_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in (request.history or [])
    ]

    response = await rag_agent_service.answer_question(
        question=request.message.strip(),
        history=history_dicts
    )

    return response

