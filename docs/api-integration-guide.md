# Factory AI API 接入说明

更新时间：2026-08-07

本文档面向需要调用 Factory AI Platform 的内部应用、脚本和自动化服务。当前 API 目标是把本地 vLLM/Qwen 能力稳定封装出来，供 EWI、MES、小工具、自动化脚本等系统通过 HTTP 调用。

## 1. 服务地址

开发环境默认地址：

```text
http://localhost:8080
```

Ubuntu 局域网访问时，将 `localhost` 替换为 Ubuntu 主机 IP，例如：

```text
http://10.69.108.253:8080
```

## 2. 接口清单

### 2.1 API 健康检查

```text
GET /api/v1/health
```

不需要认证。用于检查 Factory AI API 服务是否可用。

示例：

```bash
curl http://localhost:8080/api/v1/health
```

成功响应：

```json
{
  "status": "ok",
  "service": "Factory AI Platform",
  "model": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
  "vllm_base_url": "http://localhost:8000/v1"
}
```

### 2.2 单轮任务调用

```text
POST /api/v1/chat
```

需要 Bearer token。适合其他系统把一段任务输入交给 Factory AI，并拿到一次性的最终回答。

## 3. 认证

后端通过环境变量配置可用 token：

```bash
export API_TOKENS="factory-dev-token"
```

请求头必须包含：

```text
Authorization: Bearer factory-dev-token
```

多个 token 可用英文逗号分隔：

```bash
export API_TOKENS="line-dashboard-token,ewi-tool-token,mom-script-token"
```

当前 token 是静态配置，适合 Sprint 2 阶段的内部原型。后续如果进入正式生产，应增加 token 生命周期、调用方权限、轮换机制和审计。

## 4. 请求格式

最小请求：

```json
{
  "input": "请解释这个报警：EWI station cannot reach MOM.",
  "caller": "line-dashboard"
}
```

完整请求：

```json
{
  "input": "请解释这个报警：EWI station cannot reach MOM.",
  "caller": "line-dashboard",
  "task_type": "chat",
  "metadata": {
    "line": "G77",
    "station": "EWI",
    "work_order": "optional"
  },
  "temperature": 0.3,
  "max_tokens": 512
}
```

字段说明：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `input` | string | 是 | 无 | 用户问题或系统传入的任务内容。 |
| `caller` | string | 是 | 无 | 调用方标识，例如 `line-dashboard`、`ewi-tool`、`sn-script`。 |
| `task_type` | string | 否 | `chat` | 任务类型。Sprint 2 暂时不做复杂路由，但先保留字段。 |
| `metadata` | object | 否 | `{}` | 调用方附加信息，例如产线、站点、工单号、设备号。 |
| `temperature` | number | 否 | `0.3` | 模型采样温度，范围 `0.0` 到 `2.0`。 |
| `max_tokens` | integer | 否 | `512` | 最大输出 token，范围 `1` 到 `8192`。 |

## 5. 响应格式

成功响应：

```json
{
  "status": "ok",
  "request_id": "generated-uuid",
  "answer": "模型最终回答",
  "model": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
  "duration_ms": 1234
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | 成功时固定为 `ok`。 |
| `request_id` | string | 每次请求生成的唯一 ID，用于排查问题和关联日志。 |
| `answer` | string | 清洗后的最终回答。 |
| `model` | string | 当前后端调用的模型 ID。 |
| `duration_ms` | integer | 后端处理耗时，单位毫秒。 |

错误响应：

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

当前错误码：

| HTTP 状态码 | `error.code` | 说明 |
| --- | --- | --- |
| `401` | `unauthorized` | token 缺失或错误。 |
| `422` | `validation_error` | 请求体字段缺失、为空或超出范围。 |
| `502` | `llm_request_failed` | 后端调用 vLLM 失败。 |

## 6. curl 示例

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

Windows PowerShell 示例：

```powershell
$body = @{
  input = "Explain what this alarm means: EWI station cannot reach MOM."
  caller = "line-dashboard"
  task_type = "chat"
  metadata = @{
    line = "G77"
    station = "EWI"
  }
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://localhost:8080/api/v1/chat" `
  -Method Post `
  -Headers @{ Authorization = "Bearer factory-dev-token" } `
  -ContentType "application/json" `
  -Body $body
```

## 7. 调用日志

日志路径由环境变量控制：

```bash
export API_LOG_PATH="logs/api_calls.jsonl"
```

每次 `/api/v1/chat` 调用会写入一行 JSONL。当前记录字段：

| 字段 | 说明 |
| --- | --- |
| `timestamp` | UTC 时间戳。 |
| `request_id` | 请求唯一 ID。 |
| `caller` | 调用方标识。 |
| `task_type` | 任务类型。 |
| `metadata` | 调用方传入的附加信息。 |
| `input_chars` | 输入字符数。 |
| `status` | `ok` 或 `error`。 |
| `duration_ms` | 请求耗时。 |
| `error_code` | 失败时记录。 |
| `error_message` | 失败时记录。 |

日志不会记录完整 `input` 文本，避免将工厂现场信息、工单内容或其他敏感文本直接落盘。

查看最近日志：

```bash
tail -n 5 logs/api_calls.jsonl
```

## 8. 接入建议

- 每个调用方使用独立 `caller`，便于后续统计和排查。
- `metadata` 里放结构化信息，不要把完整问题重复塞进去。
- 调用方应保存返回的 `request_id`，方便与后端日志对应。
- 业务系统不要依赖模型回答的固定句式，只依赖 API 字段结构。
- 生产化前应增加 HTTPS、正式 token 管理、限流、持久化审计和服务监控。
