# Basic multi-tool agent in python

## Basic agent basic-agent.py

Tools:
* get_weather(city)
* get_news(topic)
* calculate(expression)

Loop:
* LLM thinks (Thought)
* select tool (Action)
* agent code executes a function
* function result returns to LLM (Action_Response)
* LLM returns Answer


## Improved agent agent.py

* same tools but implemented as a plugins, auto loaded with hot auto reload feature
* JSON only LLM results
* structured memory (tool, input output)
* parallel tool execution
* auto fix when LLM returned invalid tool name or parameters


## Tests

Tests use **pytest** and run without calling the real OpenAI API (mock `call_llm`).

### Setup

Install dev dependencies:

```bash
uv sync
```

### Run all tests

```bash
uv run pytest
```

Quiet output:

```bash
uv run pytest -q
```

Run a single file or test:

```bash
uv run pytest tests/test_agent.py
uv run pytest tests/test_tools.py::test_load_tool_registers_tool
```

### What is covered

* `tests/test_tools.py` — loading/unloading tools, hot reload handler, `system_prompt`
* `tests/test_agent.py` — parsing JSON, collecting actions, agent loop with fake LLM, retry after tool error

No `OPENAI_API_KEY` is required for pytest.

### Manual smoke test (real LLM)

To run the agent end-to-end with OpenAI:

```bash
uv run python agent.py
```

Requires `OPENAI_API_KEY` in `.env`.