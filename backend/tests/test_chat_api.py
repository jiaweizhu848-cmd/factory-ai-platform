from fastapi.testclient import TestClient

from app.main import app


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
