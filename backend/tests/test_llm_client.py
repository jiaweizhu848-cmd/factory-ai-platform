import pytest
import httpx

from app.services import llm_client
from app.services.llm_client import LlmClientError, create_chat_completion


class TransportAsyncClient(httpx.AsyncClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, transport=self.transport, **kwargs)


@pytest.fixture
def mock_vllm(monkeypatch):
    def set_response(handler):
        transport = httpx.MockTransport(handler)
        client_type = type(
            "MockedAsyncClient",
            (TransportAsyncClient,),
            {"transport": transport},
        )
        monkeypatch.setattr(llm_client.httpx, "AsyncClient", client_type)

    return set_response


@pytest.mark.asyncio
async def test_create_chat_completion_parses_vllm_response(mock_vllm):
    def handler(request):
        assert request.url == "http://localhost:8000/v1/chat/completions"
        payload = request.read()
        assert b'"stop"' in payload
        assert b'Check Against Constraints' in payload
        assert b'Check Accuracy' in payload
        assert b'Final Output Generation' in payload
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
        )

    mock_vllm(handler)

    assert await create_chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.3,
        max_tokens=512,
    ) == {"role": "assistant", "content": "ok"}


@pytest.mark.asyncio
async def test_create_chat_completion_converts_http_500_to_client_error(mock_vllm):
    def handler(request):
        return httpx.Response(500, request=request)

    mock_vllm(handler)

    with pytest.raises(LlmClientError, match="vLLM request failed"):
        await create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.3,
            max_tokens=512,
        )


@pytest.mark.asyncio
async def test_create_chat_completion_converts_non_json_body_to_format_error(mock_vllm):
    def handler(request):
        return httpx.Response(200, content=b"not json")

    mock_vllm(handler)

    with pytest.raises(LlmClientError, match="vLLM response format is invalid"):
        await create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.3,
            max_tokens=512,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": []},
    ],
)
async def test_create_chat_completion_rejects_missing_or_empty_choices(
    mock_vllm,
    body,
):
    def handler(request):
        return httpx.Response(200, json=body)

    mock_vllm(handler)

    with pytest.raises(LlmClientError, match="vLLM response format is invalid"):
        await create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.3,
            max_tokens=512,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        "not a dict",
        {"role": 123, "content": "ok"},
        {"role": "tool", "content": "ok"},
        {"role": "assistant", "content": 123},
    ],
)
async def test_create_chat_completion_rejects_invalid_message_shape(
    mock_vllm,
    message,
):
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": message}]})

    mock_vllm(handler)

    with pytest.raises(LlmClientError, match="vLLM response format is invalid"):
        await create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.3,
            max_tokens=512,
        )
