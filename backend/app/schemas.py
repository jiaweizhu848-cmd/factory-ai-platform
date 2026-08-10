from typing import Any, Literal

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


class ApiChatRequest(BaseModel):
    input: str = Field(min_length=1)
    caller: str = Field(min_length=1)
    task_type: str = Field(default="chat", min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)


class ApiChatResponse(BaseModel):
    status: Literal["ok"]
    request_id: str
    answer: str
    model: str
    duration_ms: int


class VisionAnalyzeRequest(BaseModel):
    input: str = Field(min_length=1)
    caller: str = Field(min_length=1)
    image: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1)


class AdminLoginResponse(BaseModel):
    status: Literal["ok"]
    admin_token: str


class ApiErrorDetail(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    status: Literal["error"]
    request_id: str
    error: ApiErrorDetail
