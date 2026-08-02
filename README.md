# PyAgent

**English** | [中文](README_zh.md)

A Python AI coding agent harness, inspired by [pi-mono](https://github.com/earendil-works/pi-mono) and built with LangGraph + LangChain.

PyAgent provides a modular, multi-package architecture for building AI coding agents. It supports multiple LLM providers, tool-calling loops via LangGraph, and three execution modes: interactive REPL, single-prompt pipe, and remote RPC.

## Features

- **Multi-provider LLM support** — OpenAI, Anthropic, Google Gemini, DeepSeek, and local Ollama through a unified LangChain interface
- **Tool-calling agent loop** — ReAct pattern powered by LangGraph StateGraph (Reason -> Act -> Observe -> loop)
- **Three execution modes** — Interactive REPL, single-prompt pipe (for scripting), and RPC (remote server)
- **Built-in tools** — File read/write/list, file existence check, and shell command execution
- **Terminal UI** — Rich text rendering with markdown support; optional Textual-based TUI
- **Session server** — FastAPI server with REST + NDJSON streaming endpoints
- **Persistent storage** — SQLite-backed session store via SQLModel
- **Evaluation framework** — Structured eval cases with assertions and rich report output
- **CBOR serialization** — Compact binary protocol with JSON fallback

## Architecture

```
Foundation Layer   | pyagent-ai (LLM providers via LangChain)
                   | pyagent-tui (Textual terminal UI)
                   | pyagent-protocol (message types + CBOR serialization)

Runtime Layer      | pyagent-agent (LangGraph state machine + agent loop)
                   | pyagent-client (remote session client)

Application Layer  | pyagent-coding-agent (CLI: interactive / pipe / RPC modes)

Infrastructure     | pyagent-server (FastAPI session server)
                   | pyagent-storage (SQLModel + SQLite)
                   | pyagent-evals (evaluation framework)
```

**Agent loop topology (LangGraph StateGraph):**

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
          call_model (loop back)
```

## Packages

| Package | Path | Description |
|---------|------|-------------|
| `pyagent-ai` | `packages/ai` | Unified LLM provider abstraction via LangChain |
| `pyagent-agent` | `packages/agent` | Agent runtime with LangGraph StateGraph |
| `pyagent-coding-agent` | `packages/coding_agent` | CLI application (typer + rich) |
| `pyagent-tui` | `packages/tui` | Terminal UI with Textual |
| `pyagent-protocol` | `packages/protocol` | Pydantic message models + CBOR serialization |
| `pyagent-client` | `packages/client` | Async remote session client (httpx) |
| `pyagent-server` | `packages/server` | FastAPI session server |
| `pyagent-storage` | `packages/storage` | SQLModel + SQLite persistence |
| `pyagent-evals` | `packages/evals` | Evaluation framework |

## Requirements

- **Python** >= 3.11
- An API key for at least one LLM provider (OpenAI, Anthropic, Google, or DeepSeek), or a local Ollama instance

## Installation

### Option A: Quick install (all packages at once)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/pyagent.git
cd pyagent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows (PowerShell)
# source .venv/Scripts/activate  # Windows (Git Bash)

# 3. Install all packages in editable mode (dependency order)
pip install -e packages/protocol -e packages/ai -e packages/agent \
  -e packages/storage -e packages/coding_agent -e packages/tui \
  -e packages/client -e packages/server -e packages/evals

# 4. Install dev dependencies (optional, for testing & linting)
pip install pytest pytest-asyncio ruff
```

### Option B: Using the setup script

```bash
# Unix / Git Bash
bash scripts/dev_setup.sh

# Or via Python (cross-platform)
python scripts/dev_setup.py
```

The setup script automatically creates a `.venv` and installs all packages in the correct dependency order.

### Option C: uv workspace (experimental)

The project root `pyproject.toml` includes a `[tool.uv.workspace]` configuration. If you use [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

### Verifying the installation

```bash
# Should print help text
python -m pyagent_coding_agent --help

# Or if the console script is on your PATH
pyagent --help
```

## Configuration

PyAgent reads configuration from CLI flags and environment variables. Environment variables serve as defaults; CLI flags override them.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GOOGLE_API_KEY` | — | Google Gemini API key |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `PYAGENT_MODEL_PROVIDER` | `openai` | Provider: `openai`, `anthropic`, `google`, `ollama`, `openai_compatible`, `deepseek` |
| `PYAGENT_MODEL_NAME` | `gpt-4o-mini` | Model name (e.g. `claude-3-5-sonnet-20241022`, `gemini-2.0-flash`) |
| `PYAGENT_MODEL_TEMPERATURE` | `0.7` | Sampling temperature |
| `PYAGENT_DB_PATH` | `.pyagent/sessions.db` | SQLite database path for session storage |

### Setting your API key

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google
export GOOGLE_API_KEY="AIza..."

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."

# Or use a custom OpenAI-compatible endpoint
export PYAGENT_MODEL_PROVIDER="openai_compatible"
export PYAGENT_MODEL_NAME="your-model"
# Pass --provider openai_compatible --base-url http://localhost:8000/v1 via CLI
```

### Supported models

The model registry (`pyagent_ai.models.MODEL_REGISTRY`) includes metadata for common models. A subset:

| Provider | Model | Context Window |
|----------|-------|---------------|
| OpenAI | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `o1`, `o1-mini` | 128K–200K |
| Anthropic | `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`, `claude-3-opus-20240229` | 200K |
| Google | `gemini-2.0-flash`, `gemini-1.5-pro` | 1M–2M |
| DeepSeek | `deepseek-v4-flash`, `deepseek-v4-pro` | 1M |
| Ollama | `llama3.2`, `qwen2.5` (local) | 32K–128K |

## Usage

### 1. CLI — Pipe mode (single prompt, for scripting)

```bash
# Single prompt -> stdout (tool details go to stderr)
python -m pyagent_coding_agent "What files are in this directory?"

# Select model and provider
python -m pyagent_coding_agent \
  --provider anthropic \
  --model claude-3-5-sonnet-20241022 \
  "Explain what this project does"

# Disable tools for a pure LLM response
python -m pyagent_coding_agent --no-tools "Write a haiku about Python"

# Custom system prompt
python -m pyagent_coding_agent \
  --system "You are a code reviewer. Be critical." \
  "Review the code in main.py"
```

### 2. CLI — Interactive mode (multi-turn REPL)

```bash
# Start interactive REPL
python -m pyagent_coding_agent

# Or force interactive mode even with a prompt
python -m pyagent_coding_agent --interactive

# Inside the REPL:
#   /help   - Show available commands
#   /clear  - Clear conversation history
#   /exit   - Quit the session
```

### 3. CLI — RPC mode (connect to a remote server)

```bash
# Start the server first (in another terminal)
python -m pyagent_server

# Connect to the server with a single prompt
python -m pyagent_coding_agent --rpc http://localhost:8765 "List files in this directory"

# Or interactive RPC mode
python -m pyagent_coding_agent --rpc http://localhost:8765
```

### 4. CLI flags reference

```
pyagent [PROMPT] [OPTIONS]

Arguments:
  PROMPT              Prompt text. If omitted, starts interactive mode.

Options:
  -i, --interactive   Force interactive REPL mode.
  --rpc URL           Connect to a remote pyagent-server URL (RPC mode).
  -m, --model TEXT     Model name (e.g. gpt-4o-mini, claude-3-5-sonnet).
  -p, --provider TEXT  LLM provider (openai/anthropic/google/ollama).
  -t, --temperature N  Sampling temperature. Default: 0.7
  -s, --system TEXT    Custom system prompt.
  --no-tools           Disable tool calling.
  --max-iterations N   Maximum agent loop iterations. Default: 10
  --help               Show this message and exit.
```

### 5. Python API — Using AgentSession directly

```python
from pyagent_ai import ProviderConfig, ProviderType
from pyagent_agent import AgentSession, ToolRegistry

# Configure the LLM provider
config = ProviderConfig(
    provider=ProviderType.OPENAI,
    model="gpt-4o-mini",
    temperature=0.7,
)

# Create a tool registry (optional)
registry = ToolRegistry()

# Register a custom tool
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

# Create and run the agent
session = AgentSession(
    model_config=config,
    tools=registry,
    max_iterations=10,
)

# Synchronous
response = session.run("What's the weather in Tokyo?")
print(response)

# Async
# response = await session.arun("What's the weather in Tokyo?")

# Streaming — yields (node_name, state_delta) at each graph step
for node_name, state_delta in session.stream("Read and summarize README.md"):
    print(f"[{node_name}] {state_delta}")

# Access full conversation history
history = session.get_history()

# Reset conversation (keep model + tools)
session.reset()
```

### 6. Session server (FastAPI)

```bash
# Start the server
python -m pyagent_server
# Server runs on http://127.0.0.1:8765

# Or run programmatically with custom host/port
python -c "from pyagent_server.app import run; run(host='0.0.0.0', port=9000)"
```

**REST endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/session` | Create or continue a session (returns full response) |
| `POST` | `/api/session/stream` | Stream events as NDJSON |
| `GET` | `/api/session/{id}` | Get session history |

```bash
# Create a session
curl -X POST http://localhost:8765/api/session \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'

# Health check
curl http://localhost:8765/api/health
```

### 7. Remote client (pyagent-client)

```python
from pyagent_client import RemoteSession

# Connect to a running server
with RemoteSession("http://localhost:8765") as client:
    # Multi-turn conversation (session ID maintained automatically)
    response = client.send_prompt("List files in the current directory")
    print(response)

    response = client.send_prompt("Now read the first file")
    print(response)

# Async
# async with RemoteSession("http://localhost:8765") as client:
#     response = await client.asend_prompt("Hello")

# Streaming
# for event in client.stream_prompt("Read README.md"):
#     print(event.type, event.data)
```

### 8. Session storage (pyagent-storage)

```python
from pyagent_storage import SessionStore

# Create a store (auto-creates the database file)
store = SessionStore("my_sessions.db")

# Save a session
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

# Load a session
messages = store.load_session("abc-123")

# List all sessions
sessions = store.list_sessions()

# Delete a session
store.delete_session("abc-123")
```

### 9. Evaluation framework (pyagent-evals)

```python
from pyagent_ai import ProviderConfig
from pyagent_evals import EvalRunner, EvalCase

runner = EvalRunner(config=ProviderConfig(model="gpt-4o-mini"))

# Add test cases with assertion functions
runner.add_case(EvalCase(
    name="math",
    prompt="What is 2+2? Reply with just the number.",
    assert_fn=lambda r: "4" in r,
    description="Basic arithmetic",
))

runner.add_case(EvalCase(
    name="code_gen",
    prompt="Write a Python function that returns the factorial of n.",
    assert_fn=lambda r: "def" in r and "factorial" in r.lower(),
    description="Code generation",
))

# Run all cases
results = runner.run()

# Print a rich summary table
EvalRunner.print_report(results)
```

### 10. Terminal UI (pyagent-tui)

```python
from pyagent_ai import ProviderConfig, ProviderType
from pyagent_tui.app import AgentApp

app = AgentApp(config=ProviderConfig(
    provider=ProviderType.OPENAI,
    model="gpt-4o-mini",
))
app.run()
```

### 11. Writing custom tools

```python
from pyagent_agent import ToolRegistry

registry = ToolRegistry()

# Method 1: Explicit JSON schema
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

# Method 2: Auto-inferred from function signature
def calculate(a: int, b: int, operation: str = "add") -> str:
    """Perform a calculation."""
    ...

registry.register(
    name="calculate",
    description="Perform arithmetic calculations",
    func=calculate,
    # parameters auto-inferred from type hints
)

# Method 3: Decorator (registers in the default global registry)
from pyagent_agent.tools import tool

@tool("greet", "Greet someone by name")
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

## Project Structure

```
pyagent/
├── packages/
│   ├── ai/                  # pyagent-ai: LLM provider abstraction
│   │   └── src/pyagent_ai/
│   │       ├── providers.py     # ProviderConfig + get_chat_model factory
│   │       ├── models.py        # Model registry (context windows, capabilities)
│   │       └── streaming.py     # StreamChunk + StreamHandler
│   ├── agent/               # pyagent-agent: LangGraph agent runtime
│   │   └── src/pyagent_agent/
│   │       ├── state.py        # AgentState TypedDict
│   │       ├── tools.py         # ToolRegistry + ToolSpec
│   │       ├── nodes.py         # call_model / should_continue / execute_tools
│   │       ├── graph.py         # StateGraph construction + AgentGraph wrapper
│   │       └── session.py       # AgentSession (high-level API)
│   ├── coding_agent/        # pyagent-coding-agent: CLI app
│   │   └── src/pyagent_coding_agent/
│   │       ├── cli.py           # Typer CLI (interactive / pipe / RPC)
│   │       ├── modes.py         # Mode routing logic
│   │       └── tools/
│   │           ├── file_ops.py  # read_file, write_file, list_directory, file_exists
│   │           └── shell.py     # run_command (with timeout + truncation)
│   ├── tui/                 # pyagent-tui: Textual terminal UI
│   ├── protocol/            # pyagent-protocol: Pydantic models + CBOR
│   ├── client/              # pyagent-client: HTTP remote session client
│   ├── server/              # pyagent-server: FastAPI session server
│   ├── storage/             # pyagent-storage: SQLite session persistence
│   └── evals/               # pyagent-evals: Evaluation framework
├── scripts/
│   ├── dev_setup.sh         # Unix/Git Bash setup script
│   └── dev_setup.py         # Cross-platform setup script
├── docs/
├── pyproject.toml           # Workspace root config
└── README.md
```

## Tech Stack

- **Agent**: LangGraph (StateGraph, tool-calling loop)
- **LLM**: LangChain + langchain-openai / langchain-anthropic / langchain-google-genai
- **CLI**: typer + rich
- **TUI**: Textual
- **Protocol**: Pydantic + cbor2
- **Server**: FastAPI + uvicorn
- **Client**: httpx (async)
- **Storage**: SQLModel + SQLite
- **Evals**: pytest-based framework

## Development

### Running tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run tests for a specific package
pytest packages/agent/
```

### Linting

```bash
# Install ruff
pip install ruff

# Check
ruff check packages/

# Format
ruff format packages/
```

The project uses the following ruff configuration (defined in `pyproject.toml`):

- Line length: 100
- Target: Python 3.11
- Rules: E (pycodestyle), F (pyflakes), I (isort), N (pep8-naming), W (warnings)

## Contributing

Contributions are welcome! Here's how to get started.

### Getting started

1. **Fork & clone** the repository.
2. **Set up** your development environment:

   ```bash
   python scripts/dev_setup.py
   source .venv/Scripts/activate  # or .venv/bin/activate on Unix
   ```

3. **Create a branch** for your feature or fix:

   ```bash
   git checkout -b feat/my-feature
   ```

### Coding conventions

- **Python >= 3.11** — Use modern syntax: `X | None` instead of `Optional[X]`, `match/case`, etc.
- **Type hints** — All public functions and methods should have type annotations.
- **Docstrings** — Use triple-quote docstrings for modules, classes, and public functions. Briefly describe what the code does and include a `Usage:` example for public APIs.
- **Line length** — Keep lines under 100 characters (enforced by ruff).
- **Imports** — Use `from __future__ import annotations` at the top of each module. Sort imports with ruff (isort rules).
- **Naming** — Follow PEP 8: `snake_case` for functions/variables, `PascalCase` for classes.

### Adding a new tool

1. Create a function in `packages/coding_agent/src/pyagent_coding_agent/tools/`.
2. Register it in a `register_*_tools()` function using `ToolRegistry.register()`.
3. Call the registration function in `modes.py`'s `_create_session()`.

### Adding a new LLM provider

1. Add the provider to `ProviderType` enum in `packages/ai/src/pyagent_ai/providers.py`.
2. Add an `elif` branch in `get_chat_model()` that imports and returns the appropriate LangChain chat model.
3. Add the API key environment variable to `ProviderConfig.resolve_api_key()`.
4. Add model entries to `MODEL_REGISTRY` in `packages/ai/src/pyagent_ai/models.py`.

### Adding a new package

1. Create a directory under `packages/` with `src/` layout.
2. Add a `pyproject.toml` (use an existing package as a template).
3. Add the package path to `scripts/dev_setup.py` and `scripts/dev_setup.sh`.
4. Add it to the packages table in this README.

### Commit guidelines

- Write clear, descriptive commit messages.
- Keep commits focused — one logical change per commit.
- Reference issues in commit messages when applicable (e.g., `Fix #123: ...`).

### Pull request process

1. Ensure all existing tests pass: `pytest`.
2. Run the linter: `ruff check packages/`.
3. Update documentation (README, docstrings) if your change affects the public API.
4. Open a pull request with a description of:
   - What the change does
   - Why it's needed
   - How to test it
5. Request review from a maintainer.

### Reporting bugs

When filing a bug report, please include:

- Python version and OS
- Steps to reproduce
- Expected vs. actual behavior
- Relevant error output or logs

## License

MIT
