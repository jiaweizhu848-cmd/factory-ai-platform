from datetime import UTC, datetime
import secrets
import time
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import app_info, settings
from app.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    ApiChatRequest,
    ApiChatResponse,
    ChatRequest,
    ChatResponse,
    VisionAnalyzeRequest,
)
from app.services.api_logger import summarize_api_call_logs, write_api_call_log
from app.services.llm_client import (
    LlmClientError,
    create_chat_completion,
    create_vision_completion,
)
from app.services.rate_limiter import api_rate_limiter
from app.services.response_cleaner import clean_assistant_content

DEFAULT_SYSTEM_PROMPT = (
    "你是 Factory AI。请直接回答用户问题，只输出最终答案，"
    "不要输出 Thinking Process、推理过程、草稿、内部分析或自我检查过程。"
)
VISION_SYSTEM_PROMPT = (
    "你是 Factory AI 的工业视觉助手。请直接输出可执行的最终答案，"
    "不要输出推理过程、内心分析、自我检查或草稿。"
    "如果用户要求识别或计数，请完整回答每一个子问题。"
    "对于 PCB 图片，优先按以下结构输出：1. 可见器件数量估计；"
    "2. 价格或成本范围；3. 可能应用领域；4. 不确定性和复核建议。"
    "如无法准确计数，请给出估计数量和不确定原因。"
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
    return _api_health_payload()


@app.get("/api/v1/logs/summary")
def api_v1_logs_summary(authorization: str | None = Header(default=None)):
    request_id = str(uuid4())
    if not _is_authorized(authorization):
        return _api_error(
            status_code=401,
            request_id=request_id,
            code="unauthorized",
            message="Invalid or missing bearer token",
        )

    return summarize_api_call_logs(settings.api_log_path)


@app.post("/admin/login", response_model=AdminLoginResponse)
def admin_login(request: AdminLoginRequest):
    if not secrets.compare_digest(request.password, settings.admin_password):
        return _api_error(
            status_code=401,
            request_id=str(uuid4()),
            code="unauthorized",
            message="Invalid admin password",
        )

    return AdminLoginResponse(status="ok", admin_token=settings.admin_session_token)


@app.get("/admin/api-summary")
def admin_api_summary(authorization: str | None = Header(default=None)):
    request_id = str(uuid4())
    if not _is_admin_authorized(authorization):
        return _api_error(
            status_code=401,
            request_id=request_id,
            code="unauthorized",
            message="Invalid or missing admin token",
        )

    return {
        "status": "ok",
        "health": _api_health_payload(),
        "summary": summarize_api_call_logs(settings.api_log_path),
        "rate_limit": {
            "requests": settings.api_rate_limit_requests,
            "window_seconds": settings.api_rate_limit_window_seconds,
        },
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

    rate_limit_key = _authorization_token(authorization)
    if not api_rate_limiter.allow(
        rate_limit_key,
        limit=settings.api_rate_limit_requests,
        window_seconds=settings.api_rate_limit_window_seconds,
    ):
        duration_ms = _duration_ms(started_at)
        _write_api_log(
            request_id=request_id,
            request=request,
            status="error",
            duration_ms=duration_ms,
            error_code="rate_limited",
            error_message="Too many requests",
        )
        return _api_error(
            status_code=429,
            request_id=request_id,
            code="rate_limited",
            message="Too many requests",
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


@app.post("/api/v1/vision/analyze")
async def api_v1_vision_analyze(
    request: VisionAnalyzeRequest,
    authorization: str | None = Header(default=None),
):
    request_id = str(uuid4())
    started_at = time.perf_counter()

    if not _is_authorized(authorization):
        duration_ms = _duration_ms(started_at)
        _write_vision_log(
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

    if not settings.vision_enabled:
        duration_ms = _duration_ms(started_at)
        _write_vision_log(
            request_id=request_id,
            request=request,
            status="error",
            duration_ms=duration_ms,
            error_code="vision_model_not_configured",
            error_message="Current vLLM model does not support image input",
        )
        return _api_error(
            status_code=501,
            request_id=request_id,
            code="vision_model_not_configured",
            message="Current vLLM model does not support image input",
        )

    try:
        message = await create_vision_completion(
            prompt=request.input,
            image_url=request.image,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=VISION_SYSTEM_PROMPT,
        )
    except LlmClientError:
        duration_ms = _duration_ms(started_at)
        _write_vision_log(
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
    _write_vision_log(
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
    supplied_token = _authorization_token(authorization)
    if not supplied_token:
        return False

    configured_tokens = [
        token.strip() for token in settings.api_tokens.split(",") if token.strip()
    ]
    return any(secrets.compare_digest(supplied_token, token) for token in configured_tokens)


def _is_admin_authorized(authorization: str | None) -> bool:
    supplied_token = _authorization_token(authorization)
    return bool(supplied_token) and secrets.compare_digest(
        supplied_token,
        settings.admin_session_token,
    )


def _authorization_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return ""

    return authorization.removeprefix("Bearer ").strip()


def _api_health_payload() -> dict[str, str]:
    return {
        "status": "ok",
        "service": app_info.name,
        "model": settings.vllm_model,
        "vllm_base_url": settings.vllm_base_url,
    }


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


def _write_vision_log(
    *,
    request_id: str,
    request: VisionAnalyzeRequest,
    status: str,
    duration_ms: int,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "caller": request.caller,
        "task_type": "vision",
        "metadata": request.metadata,
        "input_chars": len(request.input),
        "image_chars": len(request.image),
        "status": status,
        "duration_ms": duration_ms,
    }
    if error_code:
        entry["error_code"] = error_code
        entry["error_message"] = error_message
    write_api_call_log(settings.api_log_path, entry)
