# Basic multi-tool agent in python

## basic-agent.py

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

## agent.py

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
