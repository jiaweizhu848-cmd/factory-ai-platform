from fastapi import FastAPI, HTTPException

from app.config import app_info
from app.schemas import ChatRequest, ChatResponse
from app.services.llm_client import LlmClientError, create_chat_completion

app = FastAPI(title=app_info.name, version=app_info.version)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        message = await create_chat_completion(
            messages=[item.model_dump() for item in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except LlmClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(message=message)
