# Sprint 1: Factory AI Chat 设计规格

更新时间：2026-08-06

## 1. 目标

Sprint 1 交付一个最小可运行聊天应用：

```text
Vue 聊天页面 -> FastAPI /chat -> 本地 vLLM OpenAI API -> Qwen 回答
```

本阶段只验证应用层到本地模型服务的端到端调用。页面支持当前浏览器会话内的多轮上下文，但不保存聊天记录。

## 2. 范围

包含：

- FastAPI 后端服务。
- `POST /chat` 接口。
- 后端调用 `http://localhost:8000/v1/chat/completions`。
- Vue 3 + Vite 前端。
- 一个聊天页面。
- 前端在内存中维护当前 `messages`。
- 基础错误提示和发送中状态。

不包含：

- 登录和权限。
- 数据库。
- 聊天历史保存。
- RAG。
- 文件上传。
- AOI、MES、PLC 集成。
- 管理后台。

## 3. 架构

后端采用无状态转发：

```text
Frontend
  |
  | POST /chat { messages }
  v
Backend FastAPI
  |
  | POST /v1/chat/completions
  v
vLLM OpenAI-compatible API
  |
  v
Qwen model
```

选择无状态后端的原因：

- 第一版实现简单。
- 不需要提前设计会话表和用户体系。
- 以后可以在后端自然加入鉴权、日志、RAG 和数据库。
- 前端不直接暴露 vLLM 调用细节。

## 4. 后端设计

建议目录：

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   └── services/
│       ├── __init__.py
│       └── llm_client.py
├── tests/
│   ├── __init__.py
│   └── test_chat_api.py
└── requirements.txt
```

接口：

```text
POST /chat
```

请求：

```json
{
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.3,
  "max_tokens": 512
}
```

响应：

```json
{
  "message": {
    "role": "assistant",
    "content": "你好，我是 Qwen..."
  }
}
```

配置默认值：

- `VLLM_BASE_URL=http://localhost:8000/v1`
- `VLLM_MODEL=cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`
- `VLLM_API_KEY=EMPTY`

错误处理：

- vLLM 不可访问时返回 502。
- 请求中没有消息时返回 422。
- 最后一条消息不是用户消息时返回 422。
- vLLM 返回异常结构时返回 502。

## 5. 前端设计

建议目录：

```text
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── App.vue
    ├── main.js
    ├── api/
    │   └── chat.js
    └── style.css
```

页面结构：

- 顶部标题：Factory AI Chat。
- 中间消息列表：展示用户和 AI 回复。
- 底部输入框和发送按钮。
- 发送时禁用按钮并显示处理中状态。
- 请求失败时在页面上显示错误信息。

前端状态：

- `messages`：当前页面内完整对话。
- `input`：当前输入。
- `loading`：是否等待回复。
- `error`：请求错误。

前端请求：

```json
{
  "messages": [
    {"role": "user", "content": "第一句话"},
    {"role": "assistant", "content": "第一句回复"},
    {"role": "user", "content": "继续追问"}
  ],
  "temperature": 0.3,
  "max_tokens": 512
}
```

## 6. 测试策略

后端按 TDD 实现：

- 先写 `/chat` 成功返回 assistant message 的测试。
- 再写空消息校验测试。
- 再写 vLLM 调用失败返回 502 的测试。

前端第一版以可运行验证为主：

- `npm run build` 必须通过。
- 手动验证页面能发送消息并展示回复。

## 7. 运行方式

Ubuntu 上先启动 vLLM：

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

后端开发服务：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

前端开发服务：

```bash
cd frontend
npm install
npm run dev
```

## 8. 完成标准

Sprint 1 完成时应满足：

- 后端测试通过。
- 前端构建通过。
- vLLM 已启动时，浏览器页面可以连续问答。
- 代码和文档提交到 Git。

