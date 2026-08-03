# PyAgent

[English](README.md) | **中文**

一个 Python AI 编程 Agent 框架，灵感来自 [pi-mono](https://github.com/earendil-works/pi-mono)，基于 LangGraph + LangChain 构建。

PyAgent 提供模块化的多包架构来构建 AI 编程 Agent。它支持多种 LLM 提供商、基于 LangGraph 的工具调用循环，以及三种执行模式：交互式 REPL、单次提示管道、远程 RPC。

## 特性

- **多 LLM 提供商支持** — 通过统一的 LangChain 接口支持 OpenAI、Anthropic、Google Gemini、DeepSeek 与本地 Ollama
- **工具调用 Agent 循环** — 基于 LangGraph StateGraph 实现 ReAct 模式（推理 -> 行动 -> 观察 -> 循环）
- **三种执行模式** — 交互式 REPL、单次提示管道（适合脚本化）、RPC（远程服务器）
- **内置工具** — 文件读写/列表、文件存在检查、Shell 命令执行
- **终端界面** — Rich 文本渲染，支持 Markdown；另提供基于 Textual 的 TUI
- **会话服务器** — FastAPI 服务器，提供 REST + NDJSON 流式接口
- **持久化存储** — 基于 SQLModel + SQLite 的会话存储
- **评估框架** — 结构化测试用例，支持断言函数和富文本报告输出
- **LangSmith 追踪** — 通过 LangSmith（云端 SaaS 或本地 Docker 自托管）调试、监控和评估 LLM 调用；自动追踪 Agent 运行、LLM 调用与工具执行，记录 Token 用量、延迟与错误指标
- **CBOR 序列化** — 紧凑二进制协议，支持 JSON 回退
- **运行错误日志** — 运行时错误（含完整 traceback）自动写入轮转错误日志文件

## 架构

```
基础层 (Foundation)   | pyagent-ai (通过 LangChain 接入 LLM)
                      | pyagent-tui (Textual 终端界面)
                      | pyagent-protocol (消息类型 + CBOR 序列化)

运行时层 (Runtime)    | pyagent-agent (LangGraph 状态机 + Agent 循环)
                      | pyagent-client (远程会话客户端)

应用层 (Application)  | pyagent-coding-agent (CLI: 交互 / 管道 / RPC 模式)

基础设施 (Infra)      | pyagent-server (FastAPI 会话服务器)
                      | pyagent-storage (SQLModel + SQLite)
                      | pyagent-evals (评估框架)
```

**Agent 循环拓扑（LangGraph StateGraph）：**

```
START -> call_model -> should_continue
                          |
                +---------+---------+
                |                   |
             "tools"             "__end__"
                |
          execute_tools
                |
                v
          call_model (回到起点，继续循环)
```

## 包列表

| 包名 | 路径 | 描述 |
|------|------|------|
| `pyagent-ai` | `packages/ai` | 通过 LangChain 统一 LLM 提供商抽象 |
| `pyagent-agent` | `packages/agent` | 基于 LangGraph StateGraph 的 Agent 运行时 |
| `pyagent-coding-agent` | `packages/coding_agent` | CLI 应用（typer + rich） |
| `pyagent-tui` | `packages/tui` | 基于 Textual 的终端界面 |
| `pyagent-protocol` | `packages/protocol` | Pydantic 消息模型 + CBOR 序列化 |
| `pyagent-client` | `packages/client` | 异步远程会话客户端（httpx） |
| `pyagent-server` | `packages/server` | FastAPI 会话服务器 |
| `pyagent-storage` | `packages/storage` | SQLModel + SQLite 持久化 |
| `pyagent-evals` | `packages/evals` | 评估框架 |

## 环境要求

- **Python** >= 3.11
- 至少一个 LLM 提供商的 API Key（OpenAI、Anthropic、Google 或 DeepSeek），或本地 Ollama 实例

## 安装

### 方式 A：快速安装（一次安装所有包）

```bash
# 1. 克隆仓库
git clone https://github.com/huanglong123/pyagent.git
cd pyagent

# 2. 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows (PowerShell)
# source .venv/Scripts/activate  # Windows (Git Bash)

# 3. 按依赖顺序以可编辑模式安装所有包
pip install -e packages/protocol -e packages/ai -e packages/agent \
  -e packages/storage -e packages/coding_agent -e packages/tui \
  -e packages/client -e packages/server -e packages/evals

# 4. 安装开发依赖（可选，用于测试和代码检查）
pip install pytest pytest-asyncio ruff
```

### 方式 B：使用安装脚本

```bash
# Unix / Git Bash
bash scripts/dev_setup.sh

# 或通过 Python（跨平台）
python scripts/dev_setup.py
```

安装脚本会自动创建 `.venv` 虚拟环境，并按正确的依赖顺序安装所有包。

### 方式 C：uv workspace（实验性）

项目根目录的 `pyproject.toml` 包含 `[tool.uv.workspace]` 配置。如果你使用 [uv](https://github.com/astral-sh/uv)：

```bash
uv sync
```

### 验证安装

```bash
# 应输出帮助信息
python -m pyagent_coding_agent --help

# 如果 console_scripts 已在 PATH 中
pyagent --help
```

## 配置

PyAgent 按以下优先级从高到低读取配置：

1. **CLI 参数**（最高）——覆盖其他所有来源。
2. **真实环境变量**——通过 `export` 在 shell 中设置。
3. **`.env` 文件**——启动时自动加载（见下文）。
4. **内置默认值**（最低）——如 `gpt-4o-mini`、温度 `0.7`。

如果某个变量已在环境中设置，则**不会**使用 `.env` 文件中的值——真实环境变量始终优先。
这样你可以在 `.env` 中保留合理的默认值，同时从 shell 或 CI 覆盖单个配置，而无需修改文件。

### 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `OPENAI_API_KEY` | — | OpenAI API Key |
| `ANTHROPIC_API_KEY` | — | Anthropic API Key |
| `GOOGLE_API_KEY` | — | Google Gemini API Key |
| `DEEPSEEK_API_KEY` | — | DeepSeek API Key |
| `PYAGENT_MODEL_PROVIDER` | `openai` | 提供商：`openai`、`anthropic`、`google`、`ollama`、`openai_compatible`、`deepseek` |
| `PYAGENT_MODEL_NAME` | `gpt-4o-mini` | 模型名称（如 `claude-3-5-sonnet-20241022`、`gemini-2.0-flash`） |
| `PYAGENT_MODEL_TEMPERATURE` | `0.7` | 采样温度 |
| `PYAGENT_DB_PATH` | `.pyagent/sessions.db` | 会话存储的 SQLite 数据库路径 |
| `PYAGENT_ERROR_LOG_PATH` | `.pyagent/error.log` | 运行错误日志文件路径（按大小轮转） |
| `PYAGENT_ERROR_LOG_LEVEL` | `ERROR` | 写入错误日志的最低级别（如 `ERROR`、`WARNING`） |
| `LANGSMITH_TRACING` | `false` | 设为 `true` 启用 LangSmith 追踪所有 LLM/Agent 调用 |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API 端点（云端 URL，或本地 Docker 自托管时为 `http://localhost:1984`） |
| `LANGSMITH_API_KEY` | — | LangSmith API Key（从 https://smith.langchain.com/settings 获取） |
| `LANGSMITH_PROJECT` | `pyagent` | LangSmith 项目名称，用于分组归类追踪数据 |

### 设置 API Key

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google
export GOOGLE_API_KEY="AIza..."

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."

# 或使用自定义 OpenAI 兼容端点
export PYAGENT_MODEL_PROVIDER="openai_compatible"
export PYAGENT_MODEL_NAME="your-model"
# 通过 CLI 传 --provider openai_compatible --base-url http://localhost:8000/v1
```

### 使用 `.env` 文件

如果不想在每个 shell 里都 export 变量，可以把它们放在项目根目录的 `.env` 文件中。PyAgent 会在启动时自动加载（通过 `pyagent_ai.load_env()`，基于 [python-dotenv](https://github.com/theskumar/python-dotenv)），所有基于环境变量的配置读取都会拿到这些值。

```bash
# 复制模板并填入你的值
cp .env.example .env
```

```dotenv
# .env
DEEPSEEK_API_KEY=sk-...
PYAGENT_MODEL_PROVIDER=deepseek
PYAGENT_MODEL_NAME=deepseek-v4-flash
PYAGENT_MODEL_TEMPERATURE=0.7
PYAGENT_DB_PATH=.pyagent/sessions.db
PYAGENT_ERROR_LOG_PATH=.pyagent/error.log
PYAGENT_ERROR_LOG_LEVEL=ERROR
```

说明：

- `.env` 文件已被 git 忽略——切勿提交真实密钥。`.env.example` 是带有空值的模板。
- `load_env()` 会从当前目录向上搜索 `.env`，因此在项目子目录中运行 PyAgent 也能生效。
- 真实环境变量始终优先于 `.env` 中的值，可从 shell 覆盖单个配置而无需修改文件。
- CLI（`pyagent` 命令）和服务器（`pyagent_server.app`）都会自动加载 `.env`；若将 PyAgent 嵌入其他应用，请在读取任何配置前调用一次 `pyagent_ai.load_env()`。

### 错误日志

PyAgent 会把运行时错误（LLM API 失败、工具执行异常、网络错误、启动期崩溃——均含完整 traceback）持久化到一个按大小轮转的日志文件中，便于事后排查。CLI 与服务器在启动时通过 `pyagent_ai.setup_error_logging()` 自动启用；TUI 在构造应用时启用。若将 PyAgent 嵌入其他应用，请在启动时调用一次 `setup_error_logging()` 以获得相同行为。

```bash
# 默认位置（相对于当前工作目录）：
.pyagent/error.log          # 当前日志
.pyagent/error.log.1        # 最近一次轮转
.pyagent/error.log.2        # 更早的轮转
```

日志采用按大小轮转的 handler：每个文件增长到约 5 MB 后轮转，最多保留 3 个备份（错误日志总量大约限制在 20 MB 以内）。可通过上面的环境变量覆盖位置与级别，例如 `PYAGENT_ERROR_LOG_PATH=logs/pyagent.err`。`.gitignore` 已排除 `*.log`，错误日志不会被意外提交。

### LangSmith 追踪

PyAgent 集成了 [LangSmith](https://smith.langchain.com) 用于调试、监控和评估 LLM 应用。启用后，每次 Agent 运行、LLM 调用与工具执行都会自动作为嵌套追踪（trace）记录到 LangSmith 控制台 —— 包括输入输出、中间步骤、Token 用量、延迟与错误信息。

#### 启用追踪

设置 `LANGSMITH_TRACING=true` 并提供 API Key。CLI 会在启动时通过 `pyagent_ai.init_tracing()` 自动初始化追踪；若将 PyAgent 嵌入其他应用，请在启动时（`load_env()` 之后）调用一次 `init_tracing()`。

```dotenv
# .env — LangSmith 云端 SaaS
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=ls__your-api-key
LANGSMITH_PROJECT=pyagent
```

#### 自托管 / 本地 Docker

LangSmith 可通过 Docker 自托管。在本地运行 LangSmith 服务（参见
[部署指南](https://github.com/langchain-ai/langsmith-sdk/blob/main/docker/README.md)），
并将 `LANGSMITH_ENDPOINT` 指向它 —— 通常为 `http://localhost:1984`。

```dotenv
# .env — 自托管 LangSmith（本地 Docker）
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=http://localhost:1984
LANGSMITH_API_KEY=ls__your-local-key
LANGSMITH_PROJECT=pyagent
```

#### 追踪内容

| 追踪 span | 记录内容 |
|-----------|----------|
| `agent-run` / `agent-run-async` / `agent-stream` | 顶层 Agent 轮次：会话 ID、模型、提供商、总耗时 |
| `llm-invoke` | 每次 LLM 调用：提示消息、响应、输入/输出/总 Token 数、延迟 |
| `tool:<name>` | 每次工具执行：工具名、参数、结果、耗时 |

追踪元数据会注入用于在 LangSmith 控制台筛选：
`session_id`、`model`、`provider`、`input_tokens`、`output_tokens`、
`total_tokens`、`total_duration_ms`、`tool_<name>_duration_ms`。

#### 在代码中使用追踪 API

```python
from pyagent_ai import init_tracing, traceable, trace_context, measure_latency, TraceMetadata

# 启动时初始化一次（读取 LANGSMITH_* 环境变量）
init_tracing()

# 装饰任意函数，使其作为 LangSmith span 被捕获
@traceable(name="my-custom-step", tags=["custom"])
def my_step(x: int) -> int:
    return x + 1

# 或用上下文管理器包裹代码块
with trace_context("batch-processing", tags=["batch"]):
    with measure_latency("batch_total") as metrics:
        result = my_step(42)
    # metrics["duration_ms"] 现在持有耗时
```

#### 编程式访问 LangSmith

```python
from pyagent_ai import get_langsmith_client, get_project_runs, create_dataset

# 获取项目最近的运行记录
runs = get_project_runs(limit=100)

# 编程式创建评估数据集
create_dataset(
    dataset_name="my-evals",
    inputs=[{"input": "What is 2+2?"}],
    outputs=[{"expected": "4"}],
    description="自定义评估数据集",
)
```

#### 监控的关键指标

- **Token 用量** — 每次 LLM 调用的 `input_tokens`、`output_tokens`、`total_tokens`
- **响应时间** — 每次 Agent 运行的 `total_duration_ms`，每次 LLM 调用的 `latency_llm_invoke_ms`
- **成功率** — 失败的运行会在 LangSmith 控制台显示完整错误/traceback
- **工具性能** — 每次工具调用的 `tool_<name>_duration_ms`

#### 数据分析流程

1. 启用追踪后运行 Agent：`pyagent "your prompt"`。
2. 打开 [LangSmith 控制台](https://smith.langchain.com)（或本地 Docker 控制台）。
3. 按 `session_id`、`model`、`provider` 或 tag 筛选追踪记录。
4. 下钻查看任意追踪：输入消息、LLM 响应、工具调用与结果、Token 数量、耗时分解。
5. 使用内置评估套件（`pyagent --eval`）运行回归测试；结果会上传到 LangSmith 用于趋势追踪。

### 支持的模型

模型注册表（`pyagent_ai.models.MODEL_REGISTRY`）包含常用模型的元数据，部分列举如下：

| 提供商 | 模型 | 上下文窗口 |
|--------|------|-----------|
| OpenAI | `gpt-4o`、`gpt-4o-mini`、`gpt-4-turbo`、`o1`、`o1-mini` | 128K–200K |
| Anthropic | `claude-3-5-sonnet-20241022`、`claude-3-5-haiku-20241022`、`claude-3-opus-20240229` | 200K |
| Google | `gemini-2.0-flash`、`gemini-1.5-pro` | 1M–2M |
| DeepSeek | `deepseek-v4-flash`、`deepseek-v4-pro` | 1M |
| Ollama | `llama3.2`、`qwen2.5`（本地） | 32K–128K |

## 使用示例

### 1. CLI — 管道模式（单次提示，适合脚本化）

```bash
# 单次提示 -> stdout（工具执行详情输出到 stderr）
python -m pyagent_coding_agent "What files are in this directory?"

# 指定模型和提供商
python -m pyagent_coding_agent \
  --provider anthropic \
  --model claude-3-5-sonnet-20241022 \
  "Explain what this project does"

# 禁用工具，获取纯 LLM 回复
python -m pyagent_coding_agent --no-tools "Write a haiku about Python"

# 自定义系统提示词
python -m pyagent_coding_agent \
  --system "You are a code reviewer. Be critical." \
  "Review the code in main.py"
```

### 2. CLI — 交互模式（多轮 REPL 对话）

```bash
# 启动交互式 REPL
python -m pyagent_coding_agent

# 即使提供了提示词也强制进入交互模式
python -m pyagent_coding_agent --interactive

# REPL 内置命令：
#   /help   - 显示可用命令
#   /clear  - 清除对话历史
#   /exit   - 退出会话
```

### 3. CLI — RPC 模式（连接远程服务器）

```bash
# 先启动服务器（在另一个终端）
python -m pyagent_server

# 连接服务器并发送单次提示
python -m pyagent_coding_agent --rpc http://localhost:8765 "List files in this directory"

# 或进入交互式 RPC 模式
python -m pyagent_coding_agent --rpc http://localhost:8765
```

### 4. CLI 参数参考

```
pyagent [PROMPT] [OPTIONS]

参数：
  PROMPT              提示文本。省略则进入交互模式。

选项：
  -i, --interactive   强制交互式 REPL 模式。
  --rpc URL           连接远程 pyagent-server URL（RPC 模式）。
  -m, --model TEXT     模型名称（如 gpt-4o-mini、claude-3-5-sonnet）。
  -p, --provider TEXT  LLM 提供商（openai/anthropic/google/ollama）。
  -t, --temperature N  采样温度。默认：0.7
  -s, --system TEXT    自定义系统提示词。
  --no-tools           禁用工具调用。
  --max-iterations N   Agent 循环最大迭代次数。默认：10
  --eval               运行 LangSmith 集成的评估套件。
  --help               显示帮助信息并退出。
```

### 5. Python API — 直接使用 AgentSession

```python
from pyagent_ai import ProviderConfig, ProviderType
from pyagent_agent import AgentSession, ToolRegistry

# 配置 LLM 提供商
config = ProviderConfig(
    provider=ProviderType.OPENAI,
    model="gpt-4o-mini",
    temperature=0.7,
)

# 创建工具注册表（可选）
registry = ToolRegistry()

# 注册自定义工具
registry.register(
    name="get_weather",
    description="Get the current weather for a city",
    func=lambda city: f"The weather in {city} is sunny, 22C",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string", "description": "City name"}},
        "required": ["city"],
    },
)

# 创建并运行 Agent
session = AgentSession(
    model_config=config,
    tools=registry,
    max_iterations=10,
)

# 同步调用
response = session.run("What's the weather in Tokyo?")
print(response)

# 异步调用
# response = await session.arun("What's the weather in Tokyo?")

# 流式输出 — 在每个图节点处 yield (node_name, state_delta)
for node_name, state_delta in session.stream("Read and summarize README.md"):
    print(f"[{node_name}] {state_delta}")

# 获取完整对话历史
history = session.get_history()

# 重置对话（保留模型和工具）
session.reset()
```

### 6. 会话服务器（FastAPI）

```bash
# 启动服务器
python -m pyagent_server
# 服务器运行在 http://127.0.0.1:8765

# 或通过代码启动，自定义 host/port
python -c "from pyagent_server.app import run; run(host='0.0.0.0', port=9000)"
```

**REST 接口：**

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/session` | 创建或继续会话（返回完整响应） |
| `POST` | `/api/session/stream` | 以 NDJSON 流式返回事件 |
| `GET` | `/api/session/{id}` | 获取会话历史 |

```bash
# 创建会话
curl -X POST http://localhost:8765/api/session \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'

# 健康检查
curl http://localhost:8765/api/health
```

### 7. 远程客户端（pyagent-client）

```python
from pyagent_client import RemoteSession

# 连接到运行中的服务器
with RemoteSession("http://localhost:8765") as client:
    # 多轮对话（会话 ID 自动维护）
    response = client.send_prompt("List files in the current directory")
    print(response)

    response = client.send_prompt("Now read the first file")
    print(response)

# 异步
# async with RemoteSession("http://localhost:8765") as client:
#     response = await client.asend_prompt("Hello")

# 流式
# for event in client.stream_prompt("Read README.md"):
#     print(event.type, event.data)
```

### 8. 会话存储（pyagent-storage）

```python
from pyagent_storage import SessionStore

# 创建存储（自动创建数据库文件）
store = SessionStore("my_sessions.db")

# 保存会话
store.save_session(
    session_id="abc-123",
    messages=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ],
    system_prompt="You are a helpful assistant.",
    model_provider="openai",
    model_name="gpt-4o-mini",
)

# 加载会话
messages = store.load_session("abc-123")

# 列出所有会话
sessions = store.list_sessions()

# 删除会话
store.delete_session("abc-123")
```

### 9. 评估框架（pyagent-evals）

```python
from pyagent_ai import ProviderConfig
from pyagent_evals import EvalRunner, EvalCase

runner = EvalRunner(config=ProviderConfig(model="gpt-4o-mini"))

# 添加测试用例（带断言函数）
runner.add_case(EvalCase(
    name="math",
    prompt="What is 2+2? Reply with just the number.",
    assert_fn=lambda r: "4" in r,
    description="基础算术",
))

runner.add_case(EvalCase(
    name="code_gen",
    prompt="Write a Python function that returns the factorial of n.",
    assert_fn=lambda r: "def" in r and "factorial" in r.lower(),
    description="代码生成",
))

# 运行所有用例
results = runner.run()

# 打印富文本汇总表格
EvalRunner.print_report(results)
```

#### LangSmith 集成的评估套件

PyAgent 内置了一个精选评估数据集（`pyagent_evals.langsmith_eval.EVAL_DATASET`），
覆盖核心能力：算术、代码生成、事实知识、摘要。通过 `--eval` CLI 参数运行，
或编程式调用：

```bash
# 运行内置评估套件（若开启追踪，结果会上传到 LangSmith）
pyagent --eval

# 指定模型
pyagent --eval --provider deepseek --model deepseek-v4-flash
```

```python
from pyagent_ai import ProviderConfig
from pyagent_evals import run_langsmith_evals, compute_metrics

# 完整流程：上传数据集 -> 运行评估 -> 计算指标 -> 输出报告
result = run_langsmith_evals(
    config=ProviderConfig(model="gpt-4o-mini"),
    upload=True,  # 上传数据集到 LangSmith
)

# result["results"]  -> 每个用例的结果列表（passed、duration、tokens、error）
# result["metrics"]  -> 聚合指标（success_rate、avg_duration_ms、category_breakdown）
# result["dataset"]  -> LangSmith 数据集对象（未配置时为 None）

print(result["metrics"]["success_rate"])
```

评估套件输出的聚合指标：

| 指标 | 描述 |
|------|------|
| `success_rate` | 通过的用例比例 |
| `avg_duration_ms` | 所有用例的平均响应时间 |
| `min_duration_ms` / `max_duration_ms` | 延迟范围 |
| `category_breakdown` | 分类别成功率（math、code_gen、knowledge 等） |

### 10. 终端界面（pyagent-tui）

```python
from pyagent_ai import ProviderConfig, ProviderType
from pyagent_tui.app import AgentApp

app = AgentApp(config=ProviderConfig(
    provider=ProviderType.OPENAI,
    model="gpt-4o-mini",
))
app.run()
```

### 11. 编写自定义工具

```python
from pyagent_agent import ToolRegistry

registry = ToolRegistry()

# 方式 1：显式 JSON Schema
registry.register(
    name="search_web",
    description="Search the web and return results.",
    func=my_search_function,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results (default: 5)"},
        },
        "required": ["query"],
    },
)

# 方式 2：从函数签名自动推断参数 Schema
def calculate(a: int, b: int, operation: str = "add") -> str:
    """Perform a calculation."""
    ...

registry.register(
    name="calculate",
    description="Perform arithmetic calculations",
    func=calculate,
    # parameters 从类型提示自动推断
)

# 方式 3：装饰器（注册到默认全局注册表）
from pyagent_agent.tools import tool

@tool("greet", "Greet someone by name")
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

## 项目结构

```
pyagent/
├── packages/
│   ├── ai/                  # pyagent-ai: LLM 提供商抽象
│   │   └── src/pyagent_ai/
│   │       ├── providers.py     # ProviderConfig + get_chat_model 工厂
│   │       ├── models.py        # 模型注册表（上下文窗口、能力）
│   │       ├── streaming.py     # StreamChunk + StreamHandler
│   │       ├── tracing.py       # LangSmith 追踪集成
│   │       ├── env.py           # .env 加载（python-dotenv）
│   │       └── logging_config.py # 轮转错误日志 handler
│   ├── agent/               # pyagent-agent: LangGraph Agent 运行时
│   │   └── src/pyagent_agent/
│   │       ├── state.py        # AgentState TypedDict
│   │       ├── tools.py         # ToolRegistry + ToolSpec
│   │       ├── nodes.py         # call_model / should_continue / execute_tools
│   │       ├── graph.py         # StateGraph 构建 + AgentGraph 封装
│   │       └── session.py       # AgentSession（高级 API）
│   ├── coding_agent/        # pyagent-coding-agent: CLI 应用
│   │   └── src/pyagent_coding_agent/
│   │       ├── cli.py           # Typer CLI（交互 / 管道 / RPC）
│   │       ├── modes.py         # 模式路由逻辑
│   │       └── tools/
│   │           ├── file_ops.py  # read_file, write_file, list_directory, file_exists
│   │           └── shell.py     # run_command（带超时 + 截断）
│   ├── tui/                 # pyagent-tui: Textual 终端界面
│   ├── protocol/            # pyagent-protocol: Pydantic 模型 + CBOR
│   ├── client/              # pyagent-client: HTTP 远程会话客户端
│   ├── server/              # pyagent-server: FastAPI 会话服务器
│   ├── storage/             # pyagent-storage: SQLite 会话持久化
│   └── evals/               # pyagent-evals: 评估框架
│       └── src/pyagent_evals/
│           ├── runner.py         # EvalCase + EvalRunner
│           └── langsmith_eval.py # LangSmith 集成的评估数据集与运行器
├── scripts/
│   ├── dev_setup.sh         # Unix/Git Bash 安装脚本
│   └── dev_setup.py         # 跨平台安装脚本
├── docs/
├── pyproject.toml           # 工作区根配置
└── README.md
```

## 技术栈

- **Agent**：LangGraph（StateGraph，工具调用循环）
- **LLM**：LangChain + langchain-openai / langchain-anthropic / langchain-google-genai
- **追踪与评估**：LangSmith（调试、监控、评估）
- **CLI**：typer + rich
- **TUI**：Textual
- **协议**：Pydantic + cbor2
- **服务器**：FastAPI + uvicorn
- **客户端**：httpx（异步）
- **存储**：SQLModel + SQLite
- **评估**：基于 pytest 的框架

## 开发

### 运行测试

```bash
# 安装开发依赖
pip install pytest pytest-asyncio

# 运行所有测试
pytest

# 运行特定包的测试
pytest packages/agent/
```

### 代码检查

```bash
# 安装 ruff
pip install ruff

# 检查
ruff check packages/

# 格式化
ruff format packages/
```

项目使用以下 ruff 配置（定义在 `pyproject.toml` 中）：

- 行长度限制：100
- 目标版本：Python 3.11
- 规则：E（pycodestyle）、F（pyflakes）、I（isort）、N（pep8-naming）、W（warnings）

## 贡献指南

欢迎贡献！以下是参与方式。

### 快速上手

1. **Fork 并克隆**仓库。
2. **搭建**开发环境：

   ```bash
   python scripts/dev_setup.py
   source .venv/Scripts/activate  # Unix 上用 .venv/bin/activate
   ```

3. **创建分支**：

   ```bash
   git checkout -b feat/my-feature
   ```

### 编码规范

- **Python >= 3.11** — 使用现代语法：`X | None` 替代 `Optional[X]`、`match/case` 等。
- **类型注解** — 所有公开函数和方法都应有类型标注。
- **文档字符串** — 模块、类和公开函数使用三引号 docstring。简要描述代码功能，公开 API 附带 `Usage:` 示例。
- **行长度** — 不超过 100 字符（由 ruff 强制执行）。
- **导入** — 每个模块顶部使用 `from __future__ import annotations`。用 ruff（isort 规则）排序导入。
- **命名** — 遵循 PEP 8：函数/变量用 `snake_case`，类用 `PascalCase`。

### 添加新工具

1. 在 `packages/coding_agent/src/pyagent_coding_agent/tools/` 下创建函数。
2. 在 `register_*_tools()` 函数中用 `ToolRegistry.register()` 注册。
3. 在 `modes.py` 的 `_create_session()` 中调用注册函数。

### 添加新 LLM 提供商

1. 在 `packages/ai/src/pyagent_ai/providers.py` 的 `ProviderType` 枚举中添加提供商。
2. 在 `get_chat_model()` 中添加 `elif` 分支，导入并返回对应的 LangChain chat model。
3. 在 `ProviderConfig.resolve_api_key()` 中添加 API Key 环境变量。
4. 在 `packages/ai/src/pyagent_ai/models.py` 的 `MODEL_REGISTRY` 中添加模型条目。

### 添加新包

1. 在 `packages/` 下创建带 `src/` 布局的目录。
2. 添加 `pyproject.toml`（参考现有包作为模板）。
3. 将包路径添加到 `scripts/dev_setup.py` 和 `scripts/dev_setup.sh`。
4. 在本 README 的包列表表格中添加条目。

### 提交规范

- 编写清晰、描述性的提交信息。
- 保持提交聚焦 — 每次提交一个逻辑变更。
- 如适用，在提交信息中引用 issue（如 `Fix #123: ...`）。

### Pull Request 流程

1. 确保所有现有测试通过：`pytest`。
2. 运行代码检查：`ruff check packages/`。
3. 如果改动影响公开 API，更新文档（README、docstring）。
4. 提交 Pull Request，描述内容包括：
   - 改动做了什么
   - 为什么需要这个改动
   - 如何测试
5. 请维护者 review。

### 报告 Bug

提交 Bug 报告时，请包含：

- Python 版本和操作系统
- 复现步骤
- 预期行为与实际行为
- 相关的错误输出或日志

## 许可证

MIT
