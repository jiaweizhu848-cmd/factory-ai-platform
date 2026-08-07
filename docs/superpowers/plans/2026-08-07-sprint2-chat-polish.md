# Sprint 2 Chat Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean process-style model output, render assistant replies as Markdown, and add a clear current conversation action.

**Architecture:** The backend adds a small response cleaning service and injects a default system prompt before calling vLLM. The `/chat` API shape remains unchanged. The frontend keeps in-memory messages but renders assistant messages through Markdown and exposes a clear conversation control.

**Tech Stack:** FastAPI, Pydantic, httpx, pytest, Vue 3, Vite, marked, CSS.

---

## File Structure

- Create `backend/app/services/response_cleaner.py`: text cleanup helpers for model output.
- Create `backend/tests/test_response_cleaner.py`: unit tests for cleanup behavior.
- Modify `backend/app/main.py`: inject default system prompt and clean assistant replies before returning.
- Modify `backend/tests/test_chat_api.py`: verify prompt injection and response cleaning at route level.
- Modify `frontend/package.json`: add `marked`.
- Modify `frontend/package-lock.json`: update lockfile.
- Modify `frontend/src/App.vue`: render assistant Markdown and add clear conversation action.
- Modify `frontend/src/style.css`: add Markdown and toolbar styles.
- Modify `README.md`: document Sprint 2 behavior briefly.

---

### Task 1: Backend Response Cleaner

**Files:**
- Create: `backend/app/services/response_cleaner.py`
- Test: `backend/tests/test_response_cleaner.py`

- [ ] **Step 1: Write failing response cleaner tests**

Create `backend/tests/test_response_cleaner.py`:

```python
from app.services.response_cleaner import clean_assistant_content


def test_clean_assistant_content_extracts_final_answer():
    raw = """Thinking Process:
1. Analyze user input.
2. Draft answer.

Final Answer:
你好，我可以帮助你分析工厂数据。
"""

    assert clean_assistant_content(raw) == "你好，我可以帮助你分析工厂数据。"


def test_clean_assistant_content_removes_common_process_headings():
    raw = """Thinking Process:

Internal Monologue:

Drafting the response:

Refining the response:

可以，我会直接给出结论。
"""

    assert clean_assistant_content(raw) == "可以，我会直接给出结论。"


def test_clean_assistant_content_preserves_normal_answer():
    raw = """可以按下面步骤操作：

1. 启动 vLLM
2. 启动后端
3. 启动前端
"""

    assert clean_assistant_content(raw) == raw.strip()


def test_clean_assistant_content_falls_back_when_cleaned_empty():
    raw = "Thinking Process:"

    assert clean_assistant_content(raw) == raw
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/test_response_cleaner.py -v
```

Expected on Windows: FAIL because `app.services.response_cleaner` does not exist.  
Equivalent Ubuntu command:

```bash
source .venv/bin/activate
pytest tests/test_response_cleaner.py -v
```

- [ ] **Step 3: Implement response cleaner**

Create `backend/app/services/response_cleaner.py`:

```python
import re


FINAL_MARKER_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:Final Answer|Final|Answer)\s*:\s*",
    re.IGNORECASE,
)
PROCESS_HEADING_PATTERN = re.compile(
    r"^\s*(?:"
    r"Thinking Process|"
    r"Internal Monologue|"
    r"Drafting the response|"
    r"Refining the response"
    r")\s*:?\s*$",
    re.IGNORECASE,
)


def clean_assistant_content(content: str) -> str:
    original = content.strip()
    if not original:
        return content

    marker_match = None
    for match in FINAL_MARKER_PATTERN.finditer(original):
        marker_match = match

    if marker_match:
        cleaned = original[marker_match.end() :].strip()
        return _fallback_if_empty(cleaned, original)

    lines = []
    skipping_process_block = False
    for line in original.splitlines():
        if PROCESS_HEADING_PATTERN.match(line):
            skipping_process_block = True
            continue

        if skipping_process_block and _looks_like_process_line(line):
            continue

        skipping_process_block = False
        lines.append(line)

    cleaned = _collapse_blank_lines("\n".join(lines).strip())
    return _fallback_if_empty(cleaned, original)


def _looks_like_process_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    return bool(re.match(r"^(?:\d+\.|\*|-)\s", stripped))


def _collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)


def _fallback_if_empty(cleaned: str, original: str) -> str:
    return cleaned if cleaned else original
```

- [ ] **Step 4: Run response cleaner tests**

Run:

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/test_response_cleaner.py -v
```

Expected: PASS.

---

### Task 2: Backend Prompt Injection And Cleaned Route Response

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_chat_api.py`

- [ ] **Step 1: Write failing route tests**

Append to `backend/tests/test_chat_api.py`:

```python
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
            "content": "Thinking Process:\n1. analyze\n\nFinal Answer:\n最终回答",
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
```

- [ ] **Step 2: Run route tests to verify they fail**

Run:

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/test_chat_api.py -v
```

Expected: FAIL because prompt injection and content cleaning are not wired into `/chat`.

- [ ] **Step 3: Update route implementation**

Modify `backend/app/main.py`:

```python
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
```

- [ ] **Step 4: Run backend tests**

Run:

```bash
cd backend
.venv\Scripts\python.exe -m pytest -v
```

Expected: all backend tests pass.

---

### Task 3: Frontend Markdown Rendering And Clear Conversation

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`

- [ ] **Step 1: Add marked dependency**

Run:

```bash
cd frontend
npm install marked
```

Expected: `package.json` and `package-lock.json` update.

- [ ] **Step 2: Update App.vue**

Modify `frontend/src/App.vue`:

```vue
<script setup>
import { computed, nextTick, ref } from "vue";
import { marked } from "marked";
import { sendChat } from "./api/chat";

const welcomeMessage = {
  role: "assistant",
  content: "你好，我是 Factory AI。请输入你的问题。",
  local: true,
};

const input = ref("");
const loading = ref(false);
const error = ref("");
const messages = ref([{ ...welcomeMessage }]);
const messageList = ref(null);

const canClear = computed(() => messages.value.length > 1 || input.value || error.value);

marked.setOptions({
  breaks: true,
  gfm: true,
});

function renderMarkdown(content) {
  return marked.parse(content || "");
}

function clearConversation() {
  messages.value = [{ ...welcomeMessage }];
  input.value = "";
  error.value = "";
}

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
  const userMessageIndex = messages.value.length - 1;
  loading.value = true;
  await scrollToBottom();

  try {
    const requestMessages = messages.value.filter(
      (message) => message.role !== "system" && !message.local,
    );
    const result = await sendChat(requestMessages);
    messages.value.push(result.message);
  } catch (err) {
    messages.value.splice(userMessageIndex, 1);
    input.value = content;
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
      <div class="topbar-actions">
        <span class="service-pill">vLLM: localhost:8000</span>
        <button class="clear-button" type="button" :disabled="!canClear" @click="clearConversation">
          清空会话
        </button>
      </div>
    </header>

    <section ref="messageList" class="messages">
      <article
        v-for="(message, index) in messages"
        :key="`${message.role}-${index}`"
        class="message"
        :class="message.role"
      >
        <div class="role">{{ message.role === "user" ? "用户" : "Factory AI" }}</div>
        <div v-if="message.role === 'assistant'" class="content markdown-body" v-html="renderMarkdown(message.content)" />
        <div v-else class="content">{{ message.content }}</div>
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

- [ ] **Step 3: Add Markdown and toolbar styles**

Append or merge into `frontend/src/style.css`:

```css
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.clear-button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #c5ced6;
  border-radius: 8px;
  color: #34404a;
  background: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.clear-button:hover:not(:disabled) {
  border-color: #2f7d69;
  color: #235248;
}

.clear-button:disabled {
  color: #97a1aa;
  background: #eef1f3;
  cursor: not-allowed;
}

.markdown-body :first-child {
  margin-top: 0;
}

.markdown-body :last-child {
  margin-bottom: 0;
}

.markdown-body p,
.markdown-body ul,
.markdown-body ol,
.markdown-body pre {
  margin: 0 0 12px;
}

.markdown-body ul,
.markdown-body ol {
  padding-left: 22px;
}

.markdown-body code {
  padding: 2px 5px;
  border-radius: 4px;
  background: #edf1f4;
  font-family: "Cascadia Code", "Consolas", monospace;
  font-size: 0.92em;
}

.markdown-body pre {
  overflow-x: auto;
  padding: 12px;
  border: 1px solid #d5dbdf;
  border-radius: 8px;
  background: #182026;
  color: #f8fafc;
}

.markdown-body pre code {
  padding: 0;
  background: transparent;
  color: inherit;
}
```

In the mobile media query, add:

```css
.topbar-actions {
  justify-content: flex-start;
}
```

- [ ] **Step 4: Run frontend verification**

Run:

```bash
cd frontend
npm audit --audit-level=moderate
npm run build
```

Expected: audit has 0 moderate+ vulnerabilities and build passes.

---

### Task 4: Documentation And Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Add this section after the Sprint 1 design link:

```markdown
## 当前功能

- 本地 Qwen 多轮聊天。
- 后端自动加入默认 system prompt，减少过程性输出。
- 后端会清理常见 `Thinking Process` / `Final Answer` 包装文本。
- 前端支持 Markdown 回答展示。
- 前端支持清空当前会话。
```

- [ ] **Step 2: Run backend tests**

Run:

```bash
cd backend
.venv\Scripts\python.exe -m pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 3: Run frontend checks**

Run:

```bash
cd frontend
npm audit --audit-level=moderate
npm run build
```

Expected: audit and build pass.

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: only intended Sprint 2 source and documentation changes are present before commit.

