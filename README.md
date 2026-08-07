# Factory AI Platform

Factory AI Platform 是面向工厂场景的本地 AI 平台。当前基础 vLLM/Qwen 环境已经跑通，Sprint 1 目标是交付一个最小可运行聊天应用。

项目交接文档：[docs/PROJECT_HANDOFF.md](docs/PROJECT_HANDOFF.md)

Sprint 1 设计文档：[docs/sprint1-chat-design.md](docs/sprint1-chat-design.md)

## 当前功能

- 本地 Qwen 多轮聊天。
- 后端自动加入默认 system prompt，减少过程性输出。
- 后端会清理常见 `Thinking Process` / `Final Answer` 包装文本。
- 前端支持 Markdown 回答展示。
- 前端支持清空当前会话。

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
cd factory-ai-platform
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. 启动前端

```bash
cd factory-ai-platform
cd frontend
npm install
npm run dev
```

前端默认通过 `/api/chat` 代理到 `http://localhost:8080/chat`。  
后端默认调用 `http://localhost:8000/v1/chat/completions`。

## Sprint 2 API base

The browser chat endpoint remains available at:

```text
POST /chat
```

External applications should use the internal API endpoint:

```text
POST /api/v1/chat
```

Authentication uses a static bearer token from the backend environment:

```bash
export API_TOKENS="factory-dev-token"
export API_LOG_PATH="logs/api_calls.jsonl"
```

Example request:

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer factory-dev-token" \
  -d '{
    "input": "Explain what this alarm means: EWI station cannot reach MOM.",
    "caller": "line-dashboard",
    "task_type": "chat",
    "metadata": {
      "line": "G77",
      "station": "EWI"
    }
  }'
```

Successful response shape:

```json
{
  "status": "ok",
  "request_id": "generated-uuid",
  "answer": "model answer",
  "model": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
  "duration_ms": 1234
}
```

Error response shape:

```json
{
  "status": "error",
  "request_id": "generated-uuid",
  "error": {
    "code": "unauthorized",
    "message": "Invalid or missing bearer token"
  }
}
```

Each `/api/v1/chat` call writes one JSONL record to `API_LOG_PATH`.

