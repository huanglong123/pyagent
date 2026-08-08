# CODEBUDDY.md This file provides guidance to CodeBuddy when working with code in this repository.

## 常用命令

### 环境搭建
- `python scripts/dev_setup.py` — 以可编辑模式（`pip install -e`）安装所有工作区包及其开发依赖，并在缺失时从 `.env.example` 生成 `.env`。克隆后运行一次即可。需要 Python 3.11+。

### 构建 / 安装
- `pip install -e packages/<pkg>` — 以可编辑模式安装单个包及其依赖（如 `packages/agent`）。每个包都有独立的 `pyproject.toml`。

### 运行智能体（CLI）
- `pyagent "你的提示"` — 管道模式：输入单条提示，回复输出到 stdout，工具日志输出到 stderr。
- `pyagent` 或 `pyagent --interactive` — 交互式 REPL（命令：`/exit`、`/clear`、`/help`）。
- `pyagent --rpc http://localhost:8765 "提示"` — 通过远程 pyagent-server 的 RPC 模式。
- 常用参数：`--model/-m`、`--provider/-p`（openai/anthropic/google/ollama/openai_compatible/deepseek）、`--system/-s`、`--no-tools`、`--max-iterations`、`--temperature/-t`、`--eval`（LangSmith 评测套件）。

### 测试
- `pytest` — 在包目录下运行该包的全部测试。
- `pytest packages/<pkg>/tests/test_x.py` — 运行单个测试文件。
- `pytest packages/<pkg>/tests/test_x.py::test_name` — 运行单个测试用例。
- `pytest -k "关键字"` — 运行匹配关键字的测试。

### 代码检查 / 类型 / 格式化
- `ruff check packages/<pkg>` — 对某个包做 lint 检查。
- `ruff format packages/<pkg>` — 对某个包自动格式化。
- `mypy packages/<pkg>` — 对某个包做类型检查（每个 `pyproject.toml` 都开启了 mypy，且 `warn_unused_ignores = true`）。

### 环境配置
- 将 `.env.example` 复制为 `.env`，并设置 `PYAGENT_MODEL_PROVIDER`、`PYAGENT_MODEL_NAME` 及各 provider 的 API key。`load_env()` 负责读取 `.env`；真实环境变量优先级更高。

## 架构

PyAgent 是一个基于 **LangGraph + LangChain** 的 Python AI 编程智能体框架，采用多包工作区结构（uv 风格布局；各包位于 `packages/*` 下，使用 `src/pyagent_*` 目录布局）。各包构成一个分层栈，理解它们之间的数据流是高效开发的关键。

### 分层地图（自底向上）
1. **`pyagent-ai`**（`packages/ai`）— 基础设施层。定义 `ProviderConfig`/`ProviderType`、`load_env()`/`.env` 加载器、错误日志（`setup_error_logging`，写入受 `PYAGENT_ERROR_LOG_PATH`/`PYAGENT_ERROR_LOG_LEVEL` 控制的可滚动文件），以及 `pyagent_ai.tracing`（封装 LangSmith tracing：`init_tracing`、`get_config`、`measure_latency`、`current_metadata`）。其他所有包都依赖它。
2. **`pyagent-protocol`**（`packages/protocol`）— 客户端/服务端通信与流式传输的线格式：`messages.py`（消息类型）与 `serialization.py`（编解码）。被 RPC 路径和 `pyagent-client` 使用。
3. **`pyagent-agent`**（`packages/agent`）— 与 provider 无关的核心智能体引擎，是整个系统最核心、最需要理解的包：
   - `graph.py` — 构建 LangGraph `StateGraph`。图是一个循环：`call_model` →（`should_continue` 条件边）→ `execute_tools` → 回到 `call_model`，当没有工具调用或达到 `max_iterations` 时在 `__end__` 终止。
   - `nodes.py` — 三个 LangGraph 节点函数。`call_model` 通过 `bind_tools` 把已注册的工具绑定到 LangChain 模型、调用它，并将响应规范化为消息字典（使用 **langchain 原生的 `args` 键**而非 OpenAI 的 `arguments`，因为消息会回灌进 `model.invoke()`）。`should_continue` 强制迭代上限。`execute_tools` 通过 `ToolRegistry` 执行每个工具调用并追加 `role: "tool"` 消息；两个节点在工作时若开启 tracing 会包上 `traceable` 跨度。
   - `session.py` — `AgentSession`，对外公开 API。持有 LangGraph app 以及消息 `History`（`to_langchain()`、`from_langchain()`、`reset()`）。`run(prompt)` 执行单次完整循环；`stream(prompt)` 产出 `(节点名, 状态增量)` 元组以支持实时 UI 更新；`reset()` 清空历史。
   - `tools.py` — `ToolRegistry`（`register`、`execute`、`list_names`）与 `ToolSpec` 数据类（`name`、`description`、`func`）。工具是普通的 Python 可调用对象，被包装用于函数调用。**注意**：`pyagent-agent` 中的 `call_model` 会把 `ToolSpec` 转换为 LangChain `StructuredTool` 用于 `bind_tools`，因此工具的名称/签名必须与该路径兼容。
   - `state.py` — `AgentState` `TypedDict`（messages、tool_results、iteration、max_iterations、model、tools、system_prompt、error）与 `create_initial_state`。
   - `models.py` — `get_model(config)` 根据 `ProviderConfig` 构建 LangChain 聊天模型（连接所有 provider 的入口）。
   - `config.py` — `AgentConfig` 数据类（model_config、system_prompt、max_iterations、tools）。
4. **`pyagent-coding-agent`**（`packages/coding-agent`）— 应用层。`cli.py`（typer 应用）解析参数、构建 `ProviderConfig`、安装全局异常钩子，然后分派到 `modes.py`：
   - `run_pipe_mode` — 单条提示，最终助手消息输出到 stdout。
   - `run_interactive_mode` — 带富文本 Markdown 渲染的 REPL；注册内置工具。
   - `run_rpc_mode` — 通过 `pyagent_client.RemoteSession` 走 HTTP（无提示时回退到交互模式）。
   - `_create_session` 是共享工厂：创建 `ToolRegistry`，注册编程工具（`register_file_tools`、`register_shell_tools`，来自 `pyagent_coding_agent.tools`），并构造 `AgentSession`。
5. **`pyagent-client`**（`packages/client`）— RPC/`--rpc` 路径使用的 `RemoteSession` HTTP 客户端；借助 protocol 包与远程 `pyagent-server` 通信。
6. **`pyagent-evals`**（`packages/evals`）— `run_langsmith_evals(config, upload)`；由 CLI 的 `--eval` 参数触发。需要 `LANGSMITH_TRACING=true` 与 API key。

### 关键跨包不变量
- **工具调用形态**：助手消息必须使用 `{"type": "tool_call", "id", "name", "args"}`（langchain 原生），绝不能用 `arguments`。`nodes.py` 中有注释断言；改动工具处理时务必保留。
- **tracing 是可加性的**：每个包调用 `pyagent_ai.tracing` 辅助函数时都受 `get_config().enabled` / `LANGSMITH_TRACING` 守卫，因此关闭 tracing（默认）时代码路径保持简洁。不要破坏这些守卫。
- **错误处理**：CLI 安装全局异常钩子，将未捕获异常（除了 `KeyboardInterrupt`）记录到错误日志；模式处理函数捕获每轮异常，使 REPL/RPC 循环可存活。错误日志应走 `setup_error_logging`，而不是 `print`。
- **provider 无关的核心**：`pyagent-agent` 不得硬编码 provider；所有 provider 选择都流经 `models.get_model` + `ProviderConfig`。新增 provider 应在 `pyagent-ai`，而非智能体循环里。
- **session history 是多轮对话的唯一真源**；`reset()` 是清空它的唯一方式（被 `/clear` 使用）。

### 改动应落在何处
- 新的内置智能体能力（如新工具）→ 加到 `pyagent-coding-agent/tools`，并在 `modes._create_session` 注册。
- 新增 provider 支持 → `pyagent-ai`（`ProviderType`，以及 `pyagent-agent` 的 `get_model`）。
- 智能体循环 / 路由逻辑 → `pyagent-agent`（`graph.py`、`nodes.py`、`state.py`）。
- 线格式 / 传输改动（RPC、流式）→ `pyagent-protocol` + `pyagent-client`。
- 评测改动 → `pyagent-evals`。
