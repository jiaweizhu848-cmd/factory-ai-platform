# Factory AI Platform 项目交接文档

更新时间：2026-08-06  
当前阶段：基础模型服务已跑通，准备进入应用开发

## 1. 项目定位

Factory AI Platform 是面向工厂场景的本地 AI 平台。当前第一阶段目标不是直接做 RAG、Agent、AOI、MES 或 PLC 集成，而是先交付一个最小可用聊天系统：

```text
浏览器输入问题 -> 后端 API -> 本地 vLLM/Qwen -> 返回答案
```

第一版应保持简单，先把本地大模型能力稳定封装成可被 Web 应用调用的服务。

## 2. 当前已完成状态

根据前期配置和验证记录，基础环境已经成功跑通：

- 操作系统：Ubuntu 24.04.3 LTS
- 机器：Dell Precision 5860
- GPU：RTX 4000 Ada x2，每张约 20GB 显存
- NVIDIA Driver：595.84
- CUDA Toolkit：已配置到 `/usr/local/cuda`
- `nvcc`：已可用，版本为 13.3.73
- Python 虚拟环境：`/home/cngzf-ai/venvs/vllm`
- vLLM 服务：已成功启动
- OpenAI 兼容接口：已可访问
- 已验证模型 ID：`cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`

关键结论：模型部署工作已结束，下一步应进入应用层开发，不再继续围绕 Swagger 或手工 curl 做零散验证。

## 3. vLLM 启动方式

进入 vLLM 虚拟环境：

```bash
source /home/cngzf-ai/venvs/vllm/bin/activate
```

推荐启动命令：

```bash
vllm serve cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 16384 \
  --max-num-seqs 128 \
  --enable-prefix-caching \
  --trust-remote-code
```

说明：

- `--tensor-parallel-size 2`：使用双 GPU。
- `--max-model-len 16384`：当前建议上下文长度。
- `--max-num-seqs 128`：此前默认 256 会超过可用 Mamba cache blocks，已确认需要降低。
- `--gpu-memory-utilization 0.85`：当前稳定配置；后续如需更高并发，可再测试 0.90 左右。

## 4. API 验证方式

服务默认监听：

```text
http://localhost:8000
```

根路径 `/` 返回 404 是正常现象，因为 vLLM 没有定义首页。

可直接浏览器访问：

```text
http://localhost:8000/docs
http://localhost:8000/health
http://localhost:8000/v1/models
```

`/v1/chat/completions` 是 POST 接口，不能直接在浏览器地址栏打开。

示例请求：

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己。"}
    ],
    "temperature": 0.3,
    "max_tokens": 512
  }'
```

Python 调用示例：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",
)

resp = client.chat.completions.create(
    model="cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
    messages=[
        {"role": "user", "content": "你好"},
    ],
)

print(resp.choices[0].message.content)
```

## 5. 第一阶段开发目标

第一阶段只做 Factory AI Chat：

- 前端：Vue 3 + Vite + Element Plus
- 后端：FastAPI
- 模型：本地 vLLM OpenAI 兼容接口
- 核心功能：一个聊天页面，一个后端聊天接口

建议第一版目录：

```text
factory-ai-platform/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── routers/
│   ├── services/
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   └── package.json
├── docs/
└── README.md
```

第一阶段暂不做：

- 登录和权限
- RAG
- Agent
- OCR
- AOI 接口
- MES 接口
- PLC 接口
- 复杂菜单和管理后台

## 6. 后续阶段路线

第二阶段：Factory AI Knowledge

- 聊天记录
- Markdown 显示
- 代码高亮
- 文件上传
- PostgreSQL
- Milvus
- 工艺 SOP / 设备说明书知识库

第三阶段：Factory AI Quality

- AOI 数据接入
- MES 数据接入
- 质量异常分析
- 自动生成质量日报

第四阶段：Factory AI Maintenance

- 设备手册接入
- 维修记录接入
- 故障原因分析
- 点检和维修建议

第五阶段：Factory AI Agent

- 自动生成日报
- 查询 SQL
- 导出 Excel / PDF
- 邮件发送
- 任务编排

## 7. 当前仓库状态

截至 2026-08-06：

- Git 仓库已存在。
- 当前仓库尚未包含应用代码。
- 本文件是项目内第一份工程交接状态记录。
- 后续所有关键变更都应写入仓库文档，而不是只保存在聊天记录或个人笔记中。

## 8. 下一步建议

建议下一次开发直接从 Sprint 1 开始：

1. 创建 `backend/` FastAPI 项目。
2. 提供 `POST /chat` 接口。
3. 在后端封装对 `http://localhost:8000/v1/chat/completions` 的调用。
4. 创建 `frontend/` Vue 3 项目。
5. 做一个最小聊天页面。
6. 前端调用后端 `/chat`，完成端到端聊天。
7. 提交一次 Git commit，作为 Sprint 1 起点。

