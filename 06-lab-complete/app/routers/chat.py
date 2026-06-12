"""Chat router — endpoint /api/chat/."""
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chatbot import get_travel_response

router = APIRouter()


class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


class ChatResponse(BaseModel):
    reply: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.messages]
    reply = await get_travel_response(history)
    return ChatResponse(reply=reply)
