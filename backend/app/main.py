from datetime import UTC, datetime
import secrets
import time
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import app_info, settings
from app.schemas import ApiChatRequest, ApiChatResponse, ChatRequest, ChatResponse
from app.services.api_logger import write_api_call_log
from app.services.llm_client import LlmClientError, create_chat_completion
from app.services.response_cleaner import clean_assistant_content

DEFAULT_SYSTEM_PROMPT = (
    "你是 Factory AI。请直接回答用户问题，只输出最终答案，"
    "不要输出 Thinking Process、推理过程、草稿、内部分析或自我检查过程。"
)


app = FastAPI(title=app_info.name, version=app_info.version)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _api_error(
        status_code=422,
        request_id=str(uuid4()),
        code="validation_error",
        message="Request validation failed",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
def api_v1_health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": app_info.name,
        "model": settings.vllm_model,
        "vllm_base_url": settings.vllm_base_url,
    }


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


@app.post("/api/v1/chat", response_model=ApiChatResponse)
async def api_v1_chat(
    request: ApiChatRequest,
    authorization: str | None = Header(default=None),
):
    request_id = str(uuid4())
    started_at = time.perf_counter()

    if not _is_authorized(authorization):
        duration_ms = _duration_ms(started_at)
        _write_api_log(
            request_id=request_id,
            request=request,
            status="error",
            duration_ms=duration_ms,
            error_code="unauthorized",
            error_message="Invalid or missing bearer token",
        )
        return _api_error(
            status_code=401,
            request_id=request_id,
            code="unauthorized",
            message="Invalid or missing bearer token",
        )

    try:
        message = await create_chat_completion(
            messages=_prepare_messages([{"role": "user", "content": request.input}]),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except LlmClientError:
        duration_ms = _duration_ms(started_at)
        _write_api_log(
            request_id=request_id,
            request=request,
            status="error",
            duration_ms=duration_ms,
            error_code="llm_request_failed",
            error_message="vLLM request failed",
        )
        return _api_error(
            status_code=502,
            request_id=request_id,
            code="llm_request_failed",
            message="vLLM request failed",
        )

    answer = clean_assistant_content(message["content"])
    duration_ms = _duration_ms(started_at)
    _write_api_log(
        request_id=request_id,
        request=request,
        status="ok",
        duration_ms=duration_ms,
    )
    return ApiChatResponse(
        status="ok",
        request_id=request_id,
        answer=answer,
        model=settings.vllm_model,
        duration_ms=duration_ms,
    )


def _prepare_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    if messages and messages[0]["role"] == "system":
        return messages
    return [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}, *messages]


def _is_authorized(authorization: str | None) -> bool:
    if not authorization or not authorization.startswith("Bearer "):
        return False

    supplied_token = authorization.removeprefix("Bearer ").strip()
    configured_tokens = [
        token.strip() for token in settings.api_tokens.split(",") if token.strip()
    ]
    return any(secrets.compare_digest(supplied_token, token) for token in configured_tokens)


def _api_error(
    *,
    status_code: int,
    request_id: str,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "request_id": request_id,
            "error": {"code": code, "message": message},
        },
    )


def _duration_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))


def _write_api_log(
    *,
    request_id: str,
    request: ApiChatRequest,
    status: str,
    duration_ms: int,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "caller": request.caller,
        "task_type": request.task_type,
        "metadata": request.metadata,
        "input_chars": len(request.input),
        "status": status,
        "duration_ms": duration_ms,
    }
    if error_code:
        entry["error_code"] = error_code
        entry["error_message"] = error_message
    write_api_call_log(settings.api_log_path, entry)
