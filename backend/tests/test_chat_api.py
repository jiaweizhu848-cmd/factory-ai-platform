from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.api_logger import write_api_call_log


def test_chat_returns_assistant_message(monkeypatch):
    async def fake_create_chat_completion(messages, temperature, max_tokens):
        assert messages[0]["role"] == "system"
        assert "不要输出 Thinking Process" in messages[0]["content"]
        assert messages[1] == {"role": "user", "content": "你好"}
        assert temperature == 0.3
        assert max_tokens == 512
        return {"role": "assistant", "content": "你好，我是 Factory AI。"}

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "你好"}]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": {"role": "assistant", "content": "你好，我是 Factory AI。"}
    }


def test_chat_rejects_empty_messages():
    client = TestClient(app)
    response = client.post("/chat", json={"messages": []})

    assert response.status_code == 422


def test_chat_rejects_when_last_message_is_not_user():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "assistant", "content": "上一句回复"}]},
    )

    assert response.status_code == 422


def test_chat_returns_502_when_llm_request_fails(monkeypatch):
    from app.services.llm_client import LlmClientError

    async def fake_create_chat_completion(messages, temperature, max_tokens):
        raise LlmClientError("vLLM request failed")

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "你好"}]},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "vLLM request failed"}


def test_chat_injects_default_system_prompt(monkeypatch):
    captured = {}

    async def fake_create_chat_completion(messages, temperature, max_tokens):
        captured["messages"] = messages
        return {"role": "assistant", "content": "ok"}

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "你好"}]},
    )

    assert response.status_code == 200
    assert captured["messages"][0]["role"] == "system"
    assert "不要输出 Thinking Process" in captured["messages"][0]["content"]
    assert "推理过程" in captured["messages"][0]["content"]
    assert "草稿" in captured["messages"][0]["content"]
    assert "内部分析" in captured["messages"][0]["content"]
    assert "自我检查过程" in captured["messages"][0]["content"]
    assert captured["messages"][1] == {"role": "user", "content": "你好"}


def test_chat_does_not_duplicate_existing_system_prompt(monkeypatch):
    captured = {}

    async def fake_create_chat_completion(messages, temperature, max_tokens):
        captured["messages"] = messages
        return {"role": "assistant", "content": "ok"}

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {"role": "system", "content": "自定义系统提示"},
                {"role": "user", "content": "你好"},
            ]
        },
    )

    assert response.status_code == 200
    assert captured["messages"] == [
        {"role": "system", "content": "自定义系统提示"},
        {"role": "user", "content": "你好"},
    ]


def test_chat_returns_cleaned_assistant_message(monkeypatch):
    async def fake_create_chat_completion(messages, temperature, max_tokens):
        return {
            "role": "assistant",
            "content": """Thinking Process:
1. analyze

Final Answer:
最终回答""",
        }

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "你好"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"message": {"role": "assistant", "content": "最终回答"}}


def test_api_v1_chat_requires_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "api_tokens", "factory-token")

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"input": "hello", "caller": "test-app"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "unauthorized"
    assert body["request_id"]


def test_api_v1_chat_returns_standard_422_for_invalid_body(monkeypatch):
    monkeypatch.setattr(settings, "api_tokens", "factory-token")

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer factory-token"},
        json={"caller": "line-dashboard"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "validation_error"
    assert body["request_id"]


def test_api_v1_logs_summary_requires_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "api_tokens", "factory-token")

    client = TestClient(app)
    response = client.get("/api/v1/logs/summary")

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "unauthorized"
    assert body["request_id"]


def test_api_v1_logs_summary_returns_call_stats(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "api_tokens", "factory-token")
    monkeypatch.setattr(settings, "api_log_path", str(tmp_path / "api_calls.jsonl"))

    write_api_call_log(
        settings.api_log_path,
        {
            "timestamp": "2026-08-07T00:00:00+00:00",
            "request_id": "one",
            "caller": "line-dashboard",
            "task_type": "chat",
            "metadata": {"line": "G77"},
            "input_chars": 10,
            "status": "ok",
            "duration_ms": 100,
        },
    )
    write_api_call_log(
        settings.api_log_path,
        {
            "timestamp": "2026-08-07T00:00:01+00:00",
            "request_id": "two",
            "caller": "line-dashboard",
            "task_type": "chat",
            "metadata": {"line": "G77"},
            "input_chars": 20,
            "status": "error",
            "duration_ms": 50,
            "error_code": "llm_request_failed",
            "error_message": "vLLM request failed",
        },
    )
    write_api_call_log(
        settings.api_log_path,
        {
            "timestamp": "2026-08-07T00:00:02+00:00",
            "request_id": "three",
            "caller": "ewi-tool",
            "task_type": "chat",
            "metadata": {"line": "G77"},
            "input_chars": 30,
            "status": "ok",
            "duration_ms": 200,
        },
    )

    client = TestClient(app)
    response = client.get(
        "/api/v1/logs/summary",
        headers={"Authorization": "Bearer factory-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "total_calls": 3,
        "ok_calls": 2,
        "error_calls": 1,
        "avg_duration_ms": 117,
        "by_caller": {
            "line-dashboard": {"total": 2, "ok": 1, "error": 1},
            "ewi-tool": {"total": 1, "ok": 1, "error": 0},
        },
        "by_error_code": {"llm_request_failed": 1},
    }


def test_api_v1_health_returns_api_status_without_auth():
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "service": "Factory AI Platform",
        "model": settings.vllm_model,
        "vllm_base_url": settings.vllm_base_url,
    }
    assert "token" not in response.text.lower()


def test_admin_login_rejects_wrong_password(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "correct-password")
    monkeypatch.setattr(settings, "admin_session_token", "admin-session")

    client = TestClient(app)
    response = client.post("/admin/login", json={"password": "wrong-password"})

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "unauthorized"
    assert body["request_id"]


def test_admin_login_returns_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "correct-password")
    monkeypatch.setattr(settings, "admin_session_token", "admin-session")

    client = TestClient(app)
    response = client.post("/admin/login", json={"password": "correct-password"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "admin_token": "admin-session",
    }


def test_admin_api_summary_requires_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_session_token", "admin-session")

    client = TestClient(app)
    response = client.get("/admin/api-summary")

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "unauthorized"
    assert body["request_id"]


def test_admin_api_summary_returns_health_and_logs(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "admin_session_token", "admin-session")
    monkeypatch.setattr(settings, "api_log_path", str(tmp_path / "api_calls.jsonl"))

    write_api_call_log(
        settings.api_log_path,
        {
            "timestamp": "2026-08-07T00:00:00+00:00",
            "request_id": "one",
            "caller": "line-dashboard",
            "task_type": "chat",
            "metadata": {},
            "input_chars": 10,
            "status": "ok",
            "duration_ms": 100,
        },
    )

    client = TestClient(app)
    response = client.get(
        "/admin/api-summary",
        headers={"Authorization": "Bearer admin-session"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["health"]["model"] == settings.vllm_model
    assert body["health"]["vllm_base_url"] == settings.vllm_base_url
    assert body["summary"]["total_calls"] == 1
    assert body["rate_limit"] == {
        "requests": settings.api_rate_limit_requests,
        "window_seconds": settings.api_rate_limit_window_seconds,
    }


def test_api_v1_chat_returns_standard_response_and_logs(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "api_tokens", "factory-token")
    monkeypatch.setattr(settings, "api_log_path", str(tmp_path / "api_calls.jsonl"))

    async def fake_create_chat_completion(messages, temperature, max_tokens):
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "hello"}
        assert temperature == 0.3
        assert max_tokens == 512
        return {"role": "assistant", "content": "answer"}

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer factory-token"},
        json={
            "input": "hello",
            "caller": "line-dashboard",
            "task_type": "chat",
            "metadata": {"line": "G77"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["answer"] == "answer"
    assert body["model"] == settings.vllm_model
    assert body["request_id"]
    assert body["duration_ms"] >= 0

    log_text = (tmp_path / "api_calls.jsonl").read_text(encoding="utf-8")
    assert '"request_id":' in log_text
    assert '"caller": "line-dashboard"' in log_text
    assert '"task_type": "chat"' in log_text
    assert '"status": "ok"' in log_text


def test_api_v1_chat_logs_input_chars_without_input_text(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "api_tokens", "factory-token")
    monkeypatch.setattr(settings, "api_log_path", str(tmp_path / "api_calls.jsonl"))

    async def fake_create_chat_completion(messages, temperature, max_tokens):
        return {"role": "assistant", "content": "answer"}

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    sensitive_input = "secret machine message"
    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer factory-token"},
        json={"input": sensitive_input, "caller": "line-dashboard"},
    )

    assert response.status_code == 200
    log_text = (tmp_path / "api_calls.jsonl").read_text(encoding="utf-8")
    assert '"input_chars": 22' in log_text
    assert sensitive_input not in log_text


def test_api_v1_chat_rate_limits_per_token(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "api_tokens", "rate-limit-token")
    monkeypatch.setattr(settings, "api_log_path", str(tmp_path / "api_calls.jsonl"))
    monkeypatch.setattr(settings, "api_rate_limit_requests", 1)
    monkeypatch.setattr(settings, "api_rate_limit_window_seconds", 60)

    calls = {"count": 0}

    async def fake_create_chat_completion(messages, temperature, max_tokens):
        calls["count"] += 1
        return {"role": "assistant", "content": "answer"}

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    payload = {"input": "hello", "caller": "line-dashboard"}
    headers = {"Authorization": "Bearer rate-limit-token"}

    first_response = client.post("/api/v1/chat", headers=headers, json=payload)
    second_response = client.post("/api/v1/chat", headers=headers, json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    body = second_response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "rate_limited"
    assert body["request_id"]
    assert calls["count"] == 1

    log_text = (tmp_path / "api_calls.jsonl").read_text(encoding="utf-8")
    assert '"status": "error"' in log_text
    assert '"error_code": "rate_limited"' in log_text


def test_api_v1_chat_returns_standard_502_and_logs(monkeypatch, tmp_path):
    from app.services.llm_client import LlmClientError

    monkeypatch.setattr(settings, "api_tokens", "factory-token")
    monkeypatch.setattr(settings, "api_log_path", str(tmp_path / "api_calls.jsonl"))

    async def fake_create_chat_completion(messages, temperature, max_tokens):
        raise LlmClientError("vLLM request failed")

    monkeypatch.setattr(
        "app.main.create_chat_completion",
        fake_create_chat_completion,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer factory-token"},
        json={"input": "hello", "caller": "line-dashboard"},
    )

    assert response.status_code == 502
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "llm_request_failed"
    assert body["request_id"]

    log_text = (tmp_path / "api_calls.jsonl").read_text(encoding="utf-8")
    assert '"status": "error"' in log_text
    assert '"error_code": "llm_request_failed"' in log_text


def test_api_v1_vision_analyze_requires_bearer_token():
    client = TestClient(app)
    response = client.post(
        "/api/v1/vision/analyze",
        json={
            "input": "Analyze this PCB",
            "caller": "automate",
            "image": "data:image/jpeg;base64,abc",
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "unauthorized"
    assert body["request_id"]


def test_api_v1_vision_analyze_returns_clear_error_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "api_tokens", "factory-token")
    monkeypatch.setattr(settings, "api_log_path", str(tmp_path / "api_calls.jsonl"))
    monkeypatch.setattr(settings, "vision_enabled", False)

    client = TestClient(app)
    response = client.post(
        "/api/v1/vision/analyze",
        headers={"Authorization": "Bearer factory-token"},
        json={
            "input": "Analyze this PCB",
            "caller": "automate",
            "image": "data:image/jpeg;base64,abc",
            "metadata": {"image_name": "test.jpg"},
        },
    )

    assert response.status_code == 501
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "vision_model_not_configured"
    assert body["request_id"]

    log_text = (tmp_path / "api_calls.jsonl").read_text(encoding="utf-8")
    assert '"caller": "automate"' in log_text
    assert '"task_type": "vision"' in log_text
    assert '"image_chars": 26' in log_text
    assert '"error_code": "vision_model_not_configured"' in log_text
    assert "data:image/jpeg;base64,abc" not in log_text


def test_api_v1_vision_analyze_returns_standard_response_when_enabled(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "api_tokens", "factory-token")
    monkeypatch.setattr(settings, "api_log_path", str(tmp_path / "api_calls.jsonl"))
    monkeypatch.setattr(settings, "vision_enabled", True)

    async def fake_create_vision_completion(
        prompt,
        image_url,
        temperature,
        max_tokens,
        system_prompt,
    ):
        assert prompt == "Analyze this PCB"
        assert image_url == "data:image/jpeg;base64,abc"
        assert temperature == 0.2
        assert max_tokens == 2048
        assert "不要输出推理过程" in system_prompt
        return {"role": "assistant", "content": "vision answer"}

    monkeypatch.setattr(
        "app.main.create_vision_completion",
        fake_create_vision_completion,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/vision/analyze",
        headers={"Authorization": "Bearer factory-token"},
        json={
            "input": "Analyze this PCB",
            "caller": "automate",
            "image": "data:image/jpeg;base64,abc",
            "metadata": {"image_name": "test.jpg"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["answer"] == "vision answer"
    assert body["model"] == settings.vllm_model
    assert body["request_id"]
    assert body["duration_ms"] >= 0

    log_text = (tmp_path / "api_calls.jsonl").read_text(encoding="utf-8")
    assert '"status": "ok"' in log_text
    assert '"task_type": "vision"' in log_text
    assert '"image_chars": 26' in log_text
    assert "data:image/jpeg;base64,abc" not in log_text
