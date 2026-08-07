# Sprint 2: Chat Polish 设计规格

更新时间：2026-08-07

## 1. 目标

Sprint 2 目标是把 Sprint 1 的“能聊天”收敛成“可读、可继续使用”的聊天体验。

重点解决当前已观察到的问题：

- 模型会把 `Thinking Process`、`Internal Monologue`、`Drafting` 等过程性内容直接输出到页面。
- 前端目前只按纯文本显示，不支持 Markdown、列表、粗体和代码块。
- 当前页面没有“清空当前会话”的快捷操作。

本阶段仍然不引入数据库、登录、RAG、图片上传或历史会话。

## 2. 范围

包含：

- 后端增加模型回答清洗逻辑。
- 后端调用 vLLM 时增加 system prompt，要求只输出最终回答。
- `/chat` 返回前清洗 assistant message。
- 前端支持 Markdown 渲染。
- 前端支持代码块基础样式。
- 前端增加“清空会话”按钮。
- 后端增加清洗逻辑单元测试。
- 前端继续通过 `npm run build` 验证。

不包含：

- 聊天记录保存。
- 多会话列表。
- 数据库。
- 用户登录。
- RAG。
- 文件上传。
- 图片识别。
- 流式输出。

## 3. 推荐方案

采用“后端清洗 + Prompt 约束 + 前端 Markdown 展示”。

原因：

- 只靠前端隐藏过程文本，会让后端 API 继续返回脏内容，后续接其它客户端时还会重复处理。
- 只靠 prompt 约束不稳定，模型仍可能输出过程文本。
- 在后端统一清洗，可以让所有客户端拿到更干净的 assistant message。
- 前端 Markdown 渲染能显著改善回答可读性，尤其是列表、步骤、代码块和简单表述。

## 4. 后端设计

新增模块：

```text
backend/app/services/response_cleaner.py
```

职责：

- 接收模型原始文本。
- 移除常见过程性内容。
- 返回面向用户的最终回答。
- 如果清洗后为空，保留原文，避免误删导致空回复。

初始清洗策略：

- 如果文本包含明显的最终回答标记，例如 `Final Answer:`、`Final:`、`Answer:`，优先取这些标记之后的内容。
- 如果文本以 `Thinking Process:` 开始，并包含后续中文/英文最终回答段落，则去掉前面的过程段。
- 移除常见标题行：
  - `Thinking Process:`
  - `Internal Monologue:`
  - `Drafting the response`
  - `Refining the response`
- 对多余空行做收敛。

清洗逻辑保持保守：

- 不做复杂自然语言理解。
- 不尝试重写模型内容。
- 不删除普通业务回答中的有效列表和步骤。

后端 prompt：

在发送给 vLLM 前，如果当前 messages 没有 system message，则自动在最前面加入一个 system message：

```text
你是 Factory AI。请直接回答用户问题，只输出最终答案，不要输出 Thinking Process、推理过程、草稿、内部分析或自我检查过程。
```

如果前端未来传入 system message，后端不重复插入默认 system prompt。

## 5. API 行为

`POST /chat` 请求结构保持不变。

响应结构保持不变：

```json
{
  "message": {
    "role": "assistant",
    "content": "清洗后的最终回答"
  }
}
```

这样前端不用适配新的 API 结构。

错误处理保持 Sprint 1 行为：

- vLLM 不可访问返回 502。
- vLLM 响应结构异常返回 502。
- 请求校验失败返回 422。

## 6. 前端设计

新增依赖：

```text
marked
```

职责：

- 将 assistant message 的 Markdown 渲染为 HTML。
- 用户消息仍按纯文本展示，避免用户输入被当作 HTML。
- 渲染前使用 `marked`，并依赖 Vue 的 DOM 输出边界。当前系统是本地自用第一版，不引入复杂 sanitizer；后续如果支持外部用户，需要增加 HTML sanitization。

页面变化：

- 顶部右侧增加“清空会话”按钮。
- 清空后恢复本地欢迎语。
- assistant message 使用 Markdown 渲染。
- 代码块使用深浅适中的固定宽度字体样式。

清空会话行为：

- 只清除当前浏览器页面内存中的 `messages`。
- 不调用后端。
- 不影响 vLLM 服务。

## 7. 测试策略

后端：

- 新增 `response_cleaner` 单元测试。
- 测试 `Final Answer:` 后内容提取。
- 测试 `Thinking Process:` 过程文本移除。
- 测试没有过程文本时保持原内容。
- 测试清洗后为空时回退原文。
- 测试 `/chat` 返回内容经过清洗。
- 测试后端会为无 system message 的请求注入默认 system prompt。

前端：

- `npm run build` 必须通过。
- `npm audit --audit-level=moderate` 必须通过。
- 手动验证：
  - Markdown 列表能显示。
  - 代码块能显示。
  - 清空会话按钮能恢复欢迎语。
  - 发送失败不会污染上下文。

## 8. 完成标准

Sprint 2 完成时应满足：

- 后端测试通过。
- 前端构建通过。
- 前端依赖审计无 moderate 及以上漏洞。
- 页面不再直接显示常见 `Thinking Process` 内容。
- Markdown 回答可读。
- 当前会话可以一键清空。
- 代码推送到 GitHub。

