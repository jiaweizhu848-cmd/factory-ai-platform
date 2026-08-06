from typing import Literal

from pydantic import BaseModel, Field, field_validator


Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)

    @field_validator("messages")
    @classmethod
    def last_message_must_be_user(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        if messages[-1].role != "user":
            raise ValueError("last message must use role=user")
        return messages


class ChatResponse(BaseModel):
    message: ChatMessage
