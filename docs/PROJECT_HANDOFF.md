# Factory AI Platform 项目交接文档

更新时间：2026-08-07  
当前阶段：Sprint 2 已开始，正在建设 Factory AI API 基座  
当前主分支：`master`

## 1. 项目定位

Factory AI Platform 是面向工厂场景的本地 AI 平台。当前阶段的重点不是直接做 RAG、Agent、AOI、MES 或 PLC 集成，而是先把本地 vLLM/Qwen 能力稳定封装成一个可通过浏览器使用的最小应用。

当前已形成的端到端链路：

```text
浏览器输入任务 -> Vue 前端 -> FastAPI 后端 -> 本地 vLLM/Qwen -> 后端清洗输出 -> 前端展示
```

当前更准确的产品形态是“单轮任务助手”，而不是严格意义上的多轮聊天。实践验证显示：翻译、改写、邮件润色等任务在干净上下文下准确率更高；连续携带历史上下文会污染模型输出。

## 2. 基础环境状态

Ubuntu 侧基础模型环境已配置并验证：

- 操作系统：Ubuntu 24.04.3 LTS
- 机器：Dell Precision 5860
- GPU：RTX 4000 Ada x2，每张约 20GB 显存
- NVIDIA Driver：595.84
- CUDA Toolkit：已配置到 `/usr/local/cuda`
- `nvcc`：已可用，版本为 13.3.73
- Python vLLM 虚拟环境：`/home/cngzf-ai/venvs/vllm`
- vLLM OpenAI 兼容接口：已成功启动并可访问
- 已验证模型 ID：`cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`

推荐 vLLM 启动命令：

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

说明：

- `--tensor-parallel-size 2` 使用双 GPU。
- `--max-num-seqs 128` 是当前较稳定配置；此前更高值可能触发 cache blocks 不足。
- vLLM 服务默认监听 `http://localhost:8000`。
- `/` 返回 404 是正常现象；可检查 `/health`、`/v1/models` 或 `/docs`。

## 3. 当前应用结构

仓库当前包含可运行的前后端：

```text
backend/
  app/
    main.py
    config.py
    schemas.py
    services/
      llm_client.py
      response_cleaner.py
  tests/
  requirements.txt

frontend/
  src/
    App.vue
    api/chat.js
    main.js
    style.css
  package.json
  vite.config.js

docs/
  PROJECT_HANDOFF.md
  sprint1-chat-design.md
  sprint2-chat-polish-design.md
  superpowers/plans/
```

技术栈：

- 后端：FastAPI + httpx + pytest
- 前端：Vue 3 + Vite + marked + DOMPurify
- 模型服务：本地 vLLM OpenAI 兼容 API
- 当前代理：前端 `/api/chat` 代理到后端 `http://localhost:8080/chat`

## 4. 启动方式

### 4.1 启动 vLLM

见第 2 节推荐命令。确认 vLLM 在 Ubuntu 本机可访问：

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/models
```

### 4.2 启动后端

```bash
cd ~/Desktop/Factory_AI_Platform/backend

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

后端健康检查：

```text
http://localhost:8080/health
```

### 4.3 启动前端

```bash
cd ~/Desktop/Factory_AI_Platform/frontend

npm install
npm run dev
```

前端本机访问：

```text
http://localhost:5173
```

Windows 访问 Ubuntu 前端时，使用 Ubuntu 局域网 IP，例如：

```text
http://10.69.108.253:5173
```

如果 Windows 可以 SSH 到 Ubuntu，但浏览器访问不了：

- 确认 Vite 使用 `--host 0.0.0.0` 启动。
- 确认浏览器访问的是 Ubuntu IP，不是 Windows 自己的 `localhost`。
- 当前 UFW 状态曾显示 inactive，通常不是 UFW 拦截。

## 5. Sprint 1 已完成内容

Sprint 1 当前已暂停收尾，完成范围如下：

- 创建 FastAPI 后端服务。
- 提供 `GET /health`。
- 提供 `POST /chat`。
- 后端封装本地 vLLM `/v1/chat/completions` 调用。
- 后端自动注入默认 system prompt，要求只输出最终答案。
- 后端实现响应清洗器，处理常见过程输出泄漏。
- 创建 Vue 3 + Vite 前端。
- 实现浏览器输入、发送、加载状态、错误提示、清空会话。
- 实现 Markdown 渲染，并用 DOMPurify 做 HTML 清洗。
- 调整聊天窗口布局，使其更适配浏览器缩放和视口高度。
- 将前端请求策略改为“只发送最新一条用户消息”，避免历史上下文污染。
- 将代码推送到 GitHub：`https://github.com/jiaweizhu848-cmd/factory-ai-platform.git`

当前最新关键提交：

- `77797b9 fix: send only latest user message`
- `0459b8a fix: avoid returning process-only responses`
- `e7661f9 fix: remove vllm stop sequences to avoid truncation`
- `5ebb022 fix: clean partial accuracy reasoning heading`
- `d1199dc fix: stop accuracy tone reasoning sections`

## 5.1 Sprint 2 已开始内容

Sprint 2 第一批能力已落地：

- 新增面向外部系统调用的 `POST /api/v1/chat`。
- 支持静态 Bearer token 认证，配置项为 `API_TOKENS`。
- 支持标准响应字段：`status`、`request_id`、`answer`、`model`、`duration_ms`。
- 支持标准错误响应，当前覆盖 401、422、502。
- 支持 JSONL 调用日志，配置项为 `API_LOG_PATH`，默认 `logs/api_calls.jsonl`。
- 新增 `GET /api/v1/health`，便于其他系统检查 Factory AI API 状态。
- 新增 `GET /api/v1/logs/summary`，便于查看调用总量、成功/失败数量、平均耗时、caller 分布和错误码分布。
- JSONL 调用日志已记录 `input_chars`，但不记录完整输入文本，降低敏感工厂信息落盘风险。
- 新增内存级按 token 限流，默认 60 秒 60 次；超限返回 429 / `rate_limited`。
- 新增内部系统接入说明：[docs/api-integration-guide.md](api-integration-guide.md)。
- 当前网页 `/chat` 保持可用，不受外部 API token 影响。

## 6. 关键经验和决策记录

### 6.1 默认不再发送完整历史上下文

实测规律：

- 第一次问翻译/改写任务，准确率通常较高。
- 在同一会话中重复同一内容，结果会越来越偏。
- 点击“清空会话”后再问同样问题，准确率恢复。

结论：

对当前主要任务类型，历史上下文是噪音，不是帮助。因此前端现在保留聊天记录用于查看，但每次 API 请求只发送最新一条用户输入。

后续如果需要真正多轮对话，应加一个显式“连续对话模式”开关，而不是默认开启。

### 6.2 不再使用 vLLM stop sequences

曾尝试给 vLLM 请求加入 `stop`，用于提前终止 `Thinking Process`、`Check Accuracy` 等过程段落。

问题：

- stop 词会误截断正常技术文本。
- 例如 IP、服务器地址、编号标题等内容可能被提前切掉。

当前决策：

- 移除 vLLM `stop` 参数。
- 让模型完整生成。
- 后端 `response_cleaner.py` 负责清理过程段。

### 6.3 响应清洗器是当前必要防线

本地 Qwen 模型会偶发输出以下过程段：

- `Thinking Process`
- `Here's a thinking process`
- `Check Constraints`
- `Check Against Constraints`
- `Check Accuracy & Tone`
- `Final Output Generation`
- `Self-Correction/Verification`
- `Output matches`
- `Proceed`
- `Done`

当前后端会尽量清理这些内容。若模型只返回过程、没有最终答案，后端返回固定提示：

```text
抱歉，这次模型没有返回可展示的最终答案，请重新提问。
```

## 7. 当前验证状态

截至 2026-08-07 最近一次验证：

后端：

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

结果：

```text
37 passed
```

前端：

```bash
cd frontend
npm audit --audit-level=moderate
npm run build
```

结果：

```text
0 vulnerabilities
vite build passed
```

## 8. 已知限制

- 当前不是完整多轮对话产品；默认是单轮任务助手。
- 前端副标题仍显示“本地 Qwen 多轮对话”，建议下一步修正文案。
- 后端清洗器仍是规则型方案，长期不应无限堆规则。
- 目前没有前端单元测试框架。
- 没有持久化聊天记录。
- 没有任务类型选择，例如“翻译 / 润色 / 总结 / 问答”。
- 没有文件上传。
- 没有用户登录、权限、审计。
- 没有 RAG、知识库、向量数据库。

## 9. 下一步建议开发

下一阶段应避免把 Factory AI Platform 做成普通办公聊天工具。翻译、润色、总结等通用能力已有成熟 ChatGPT 工具，项目后续应更明确地靠近工业现场场景。

建议后续围绕三条工业主线推进：

1. 工业视觉理解
   - 面向现场图片、设备铭牌、报警截图、WI 页面、质量缺陷图。
   - 支持上传图片并返回结构化理解结果。
   - 输出应包含：识别对象、关键文字/OCR、异常点、风险等级、建议动作。
   - 后续可扩展到 AOI 图片、维修照片、点检照片和异常复判。

2. Factory AI API 网关
   - 将本地 Qwen/vLLM 能力封装成可被其他系统调用的内部 API。
   - 支持 API token、调用日志、调用方标识、基础限流和错误追踪。
   - 面向 MES、EWI、ServiceNow、小工具、自动化脚本等系统集成。
   - 这是从“网页聊天”升级到“本地 AI 能力服务”的关键底座。

3. WI / SOP 智能体
   - 训练或接入 WI、SOP、设备手册、异常处理流程。
   - 让线上工人可以用自然语言提问。
   - 回答需要引用来源文档、章节、页码或段落。
   - 后续按角色扩展：操作员助手、维修助手、质量助手、工艺助手。

推荐新的 Sprint 2：

```text
Sprint 2：Factory AI API 基座
目标：把当前本地 Qwen 能力封装成可被其他应用调用的内部 API 服务，支持 API token、调用日志和稳定的单轮任务接口。
```

Sprint 2 建议范围：

1. API token 认证
   - 新增简单 token 表或配置文件。
   - 外部请求必须带 `Authorization: Bearer <token>`。
   - 先支持静态 token，后续再做管理页面。

2. 标准化 API
   - 保留当前网页 `/chat` 能力。
   - 新增面向系统调用的 `/api/v1/chat` 或 `/api/v1/tasks`。
   - 请求体包含：`input`、`caller`、`task_type`、`metadata`。
   - 响应体包含：`answer`、`request_id`、`model`、`duration_ms`、`status`。

3. 调用日志
   - 记录每次请求的时间、调用方、任务类型、耗时、状态、错误信息。
   - Sprint 2 可先落地为本地 SQLite 或 JSONL 日志。
   - 后续再迁移到 PostgreSQL。

4. 稳定性和可观测性
   - 每次请求生成 `request_id`。
   - 后端日志包含 `request_id`，方便排查。
   - 明确 401、422、502 等错误返回格式。

5. 文档和示例
   - 在 README 或 docs 中提供 curl 示例。
   - 给其他应用调用 Factory AI 的最小样例。

Sprint 2 暂不做：

- 用户登录和 Web 管理后台
- 数据库复杂权限模型
- RAG 文档知识库
- 图片上传和视觉模型
- Agent 编排
- MES/AOI/PLC 正式接入

建议 Sprint 3：

```text
Sprint 3：WI / SOP 知识问答原型
目标：支持上传或导入少量 WI/SOP 文档，建立最小知识检索链路，让现场工人能基于文档问答。
```

建议 Sprint 4：

```text
Sprint 4：工业视觉理解原型
目标：支持上传现场图片、报警截图或设备铭牌图片，返回 OCR、对象识别、异常描述和建议动作。
```

## 10. 建议的下一条开发指令

下一次可以直接从这里开始：

```text
开始 Sprint 2：建设 Factory AI API 基座。新增面向其他应用调用的 /api/v1/chat 接口，支持 Bearer token 认证、request_id、调用日志、标准错误返回和 curl 调用示例。当前网页 Chat 保持可用。
```
