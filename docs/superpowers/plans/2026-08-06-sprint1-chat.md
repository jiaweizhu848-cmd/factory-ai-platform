# Sprint 1 Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal Factory AI Chat app where a Vue page sends multi-turn messages to FastAPI, and FastAPI forwards them to the local vLLM OpenAI-compatible API.

**Architecture:** The frontend owns the current in-browser conversation state and posts full `messages` to `POST /chat`. The backend is stateless and validates the request before calling `http://localhost:8000/v1/chat/completions`. No database, login, RAG, or history persistence is included.

**Tech Stack:** FastAPI, Pydantic, httpx, pytest, Vue 3, Vite, JavaScript, CSS.

---

## File Structure

- Create `backend/requirements.txt`: Python dependencies for app and tests.
- Create `backend/app/__init__.py`: package marker.
- Create `backend/app/config.py`: environment-based vLLM settings.
- Create `backend/app/schemas.py`: request and response schemas.
- Create `backend/app/services/__init__.py`: service package marker.
- Create `backend/app/services/llm_client.py`: vLLM client wrapper.
- Create `backend/app/main.py`: FastAPI app and `/chat` route.
- Create `backend/tests/__init__.py`: test package marker.
- Create `backend/tests/test_chat_api.py`: backend API tests.
- Create `frontend/package.json`: frontend scripts and dependencies.
- Create `frontend/index.html`: Vite entry HTML.
- Create `frontend/vite.config.js`: dev server proxy from `/api` to backend.
- Create `frontend/src/main.js`: Vue app mount.
- Create `frontend/src/api/chat.js`: frontend API wrapper.
- Create `frontend/src/App.vue`: chat UI and state.
- Create `frontend/src/style.css`: application styling.
- Modify `README.md`: add run instructions.

---

### Task 1: Backend Dependencies And Schemas

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/schemas.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Write dependencies**

Create `backend/requirements.txt`:

```text
fastapi==0.116.1
uvicorn[standard]==0.35.0
httpx==0.28.1
pytest==8.4.1
pytest-asyncio==1.1.0
```

- [ ] **Step 2: Create package markers**

Create empty files:

```text
backend/app/__init__.py
backend/tests/__init__.py
```

- [ ] **Step 3: Write configuration**

Create `backend/app/config.py`:

```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit"
    vllm_api_key: str = "EMPTY"
    request_timeout_seconds: float = 120.0

    model_config = SettingsConfigDict(env_prefix="", env_file=".env")


class AppInfo(BaseModel):
    name: str = "Factory AI Platform"
    version: str = "0.1.0"


settings = Settings()
app_info = AppInfo()
```

- [ ] **Step 4: Add missing dependency**

Because `pydantic_settings` is used, add it to `backend/requirements.txt`:

```text
pydantic-settings==2.10.1
```

- [ ] **Step 5: Write schemas**

Create `backend/app/schemas.py`:

```python
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
```

- [ ] **Step 6: Install backend dependencies**

Run:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: packages install without errors.

---

### Task 2: Backend Chat API With TDD

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/llm_client.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_chat_api.py`

- [ ] **Step 1: Write failing success test**

Create `backend/tests/test_chat_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_chat_returns_assistant_message(monkeypatch):
    async def fake_create_chat_completion(messages, temperature, max_tokens):
        assert messages == [{"role": "user", "content": "你好"}]
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_chat_api.py::test_chat_returns_assistant_message -v
```

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Write minimal app and stub client**

Create `backend/app/services/__init__.py` as an empty file.

Create `backend/app/services/llm_client.py`:

```python
import httpx

from app.config import settings


class LlmClientError(RuntimeError):
    pass


async def create_chat_completion(
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> dict[str, str]:
    payload = {
        "model": settings.vllm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {settings.vllm_api_key}"}

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.vllm_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LlmClientError("vLLM request failed") from exc

    data = response.json()
    try:
        message = data["choices"][0]["message"]
        return {"role": message["role"], "content": message["content"]}
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmClientError("vLLM response format is invalid") from exc
```

Create `backend/app/main.py`:

```python
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
```

- [ ] **Step 4: Run success test to verify it passes**

Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_chat_api.py::test_chat_returns_assistant_message -v
```

Expected: PASS.

- [ ] **Step 5: Write failing validation and gateway tests**

Append to `backend/tests/test_chat_api.py`:

```python
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
```

- [ ] **Step 6: Run backend tests**

Run:

```bash
cd backend
source .venv/bin/activate
pytest -v
```

Expected: all tests pass.

---

### Task 3: Frontend Chat App

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.js`
- Create: `frontend/src/main.js`
- Create: `frontend/src/api/chat.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/style.css`

- [ ] **Step 1: Create frontend package**

Create `frontend/package.json`:

```json
{
  "name": "factory-ai-chat",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vite build",
    "preview": "vite preview --host 0.0.0.0"
  },
  "dependencies": {
    "@vitejs/plugin-vue": "5.2.4",
    "vite": "5.4.19",
    "vue": "3.5.18"
  },
  "devDependencies": {}
}
```

- [ ] **Step 2: Create Vite entry files**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Factory AI Chat</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

Create `frontend/vite.config.js`:

```javascript
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
```

Create `frontend/src/main.js`:

```javascript
import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";

createApp(App).mount("#app");
```

- [ ] **Step 3: Create API wrapper**

Create `frontend/src/api/chat.js`:

```javascript
export async function sendChat(messages) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      messages,
      temperature: 0.3,
      max_tokens: 512,
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "聊天请求失败");
  }

  return response.json();
}
```

- [ ] **Step 4: Create chat UI**

Create `frontend/src/App.vue`:

```vue
<script setup>
import { nextTick, ref } from "vue";
import { sendChat } from "./api/chat";

const input = ref("");
const loading = ref(false);
const error = ref("");
const messages = ref([
  {
    role: "assistant",
    content: "你好，我是 Factory AI。请输入你的问题。",
  },
]);
const messageList = ref(null);

async function scrollToBottom() {
  await nextTick();
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight;
  }
}

async function submitMessage() {
  const content = input.value.trim();
  if (!content || loading.value) {
    return;
  }

  error.value = "";
  input.value = "";
  messages.value.push({ role: "user", content });
  loading.value = true;
  await scrollToBottom();

  try {
    const requestMessages = messages.value.filter((message) => message.role !== "system");
    const result = await sendChat(requestMessages);
    messages.value.push(result.message);
  } catch (err) {
    error.value = err.message || "聊天请求失败";
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <h1>Factory AI Chat</h1>
        <p>本地 Qwen 多轮对话</p>
      </div>
      <span class="service-pill">vLLM: localhost:8000</span>
    </header>

    <section ref="messageList" class="messages">
      <article
        v-for="(message, index) in messages"
        :key="`${message.role}-${index}`"
        class="message"
        :class="message.role"
      >
        <div class="role">{{ message.role === "user" ? "用户" : "Factory AI" }}</div>
        <div class="content">{{ message.content }}</div>
      </article>
      <article v-if="loading" class="message assistant">
        <div class="role">Factory AI</div>
        <div class="content">正在思考...</div>
      </article>
    </section>

    <p v-if="error" class="error">{{ error }}</p>

    <form class="composer" @submit.prevent="submitMessage">
      <textarea
        v-model="input"
        placeholder="输入问题，按 Ctrl+Enter 发送"
        :disabled="loading"
        @keydown.ctrl.enter.prevent="submitMessage"
      />
      <button type="submit" :disabled="loading || !input.trim()">
        {{ loading ? "发送中" : "发送" }}
      </button>
    </form>
  </main>
</template>
```

- [ ] **Step 5: Create styles**

Create `frontend/src/style.css`:

```css
:root {
  color: #17212f;
  background: #eef2f5;
  font-family: "Segoe UI", Arial, sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

button,
textarea {
  font: inherit;
}

.app-shell {
  display: grid;
  grid-template-rows: auto 1fr auto auto;
  height: 100vh;
  max-width: 1120px;
  margin: 0 auto;
  background: #ffffff;
  border-left: 1px solid #d8dee6;
  border-right: 1px solid #d8dee6;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 68px;
  padding: 14px 24px;
  border-bottom: 1px solid #d8dee6;
}

.topbar h1 {
  margin: 0;
  font-size: 20px;
}

.topbar p {
  margin: 4px 0 0;
  color: #667085;
  font-size: 13px;
}

.service-pill {
  flex: 0 0 auto;
  padding: 6px 10px;
  border: 1px solid #b7d6c4;
  border-radius: 999px;
  color: #146c43;
  background: #edf8f1;
  font-size: 13px;
}

.messages {
  overflow-y: auto;
  padding: 24px;
  background: #f7f9fb;
}

.message {
  max-width: 780px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #d8dee6;
  border-radius: 8px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.message.user {
  margin-left: auto;
  background: #e8f2ff;
}

.message.assistant {
  background: #ffffff;
}

.role {
  margin-bottom: 6px;
  color: #667085;
  font-size: 12px;
  font-weight: 700;
}

.error {
  margin: 0;
  padding: 10px 24px;
  color: #b42318;
  background: #fff1f0;
  border-top: 1px solid #ffd6d2;
}

.composer {
  display: grid;
  grid-template-columns: 1fr 96px;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #d8dee6;
}

.composer textarea {
  min-height: 52px;
  max-height: 140px;
  resize: vertical;
  padding: 12px;
  border: 1px solid #c7d0da;
  border-radius: 8px;
  outline: none;
}

.composer textarea:focus {
  border-color: #cf1322;
  box-shadow: 0 0 0 3px rgba(207, 19, 34, 0.12);
}

.composer button {
  border: 0;
  border-radius: 8px;
  color: #ffffff;
  background: #cf1322;
  font-weight: 700;
  cursor: pointer;
}

.composer button:disabled {
  cursor: not-allowed;
  background: #9ca3af;
}

@media (max-width: 720px) {
  .app-shell {
    border: 0;
  }

  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .composer {
    grid-template-columns: 1fr;
  }

  .composer button {
    height: 44px;
  }
}
```

- [ ] **Step 6: Build frontend**

Run:

```bash
cd frontend
npm install
npm run build
```

Expected: Vite build completes successfully.

---

### Task 4: README And Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README run instructions**

Replace `README.md` with:

```markdown
# Factory AI Platform

Factory AI Platform 是面向工厂场景的本地 AI 平台。当前基础 vLLM/Qwen 环境已经跑通，Sprint 1 目标是交付一个最小可运行聊天应用。

项目交接文档：[docs/PROJECT_HANDOFF.md](docs/PROJECT_HANDOFF.md)

Sprint 1 设计文档：[docs/sprint1-chat-design.md](docs/sprint1-chat-design.md)

## 运行顺序

### 1. 启动 vLLM

```bash
source /home/cngzf-ai/venvs/vllm/bin/activate

vllm serve cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 16384 \
  --max-num-seqs 128 \
  --enable-prefix-caching \
  --trust-remote-code
```

### 2. 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认通过 `/api/chat` 代理到 `http://localhost:8080/chat`。
后端默认调用 `http://localhost:8000/v1/chat/completions`。
```

- [ ] **Step 2: Run backend tests**

Run:

```bash
cd backend
source .venv/bin/activate
pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: build passes.

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: only intended Sprint 1 files are modified or added.

