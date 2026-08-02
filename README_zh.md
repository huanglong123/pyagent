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
- **CBOR 序列化** — 紧凑二进制协议，支持 JSON 回退

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
git clone https://github.com/your-org/pyagent.git
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

PyAgent 从 CLI 参数和环境变量读取配置。环境变量作为默认值，CLI 参数会覆盖环境变量。

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
│   │       └── streaming.py     # StreamChunk + StreamHandler
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
