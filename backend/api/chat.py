from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Literal

from services.ai_service import generate_response


router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    messages = [
        message.model_dump()
        for message in request.messages
    ]

    response = generate_response(messages)

    return {
        "response": response
    }