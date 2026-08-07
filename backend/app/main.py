from fastapi import FastAPI, HTTPException

from app.config import app_info
from app.schemas import ChatRequest, ChatResponse
from app.services.llm_client import LlmClientError, create_chat_completion
from app.services.response_cleaner import clean_assistant_content

DEFAULT_SYSTEM_PROMPT = (
    "你是 Factory AI。请直接回答用户问题，只输出最终答案，"
    "不要输出 Thinking Process、推理过程、草稿、内部分析或自我检查过程。"
)


app = FastAPI(title=app_info.name, version=app_info.version)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        message = await create_chat_completion(
            messages=_prepare_messages([item.model_dump() for item in request.messages]),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except LlmClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    message["content"] = clean_assistant_content(message["content"])
    return ChatResponse(message=message)


def _prepare_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    if messages and messages[0]["role"] == "system":
        return messages
    return [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}, *messages]
