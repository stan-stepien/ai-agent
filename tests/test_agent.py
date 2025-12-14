import json
import textwrap

import agent


def test_normalize_parsed_list():
    data = [{"type": "action", "name": "get_weather", "input": "Warsaw"}]
    assert agent.normalize_parsed(data) == data


def test_normalize_parsed_dict():
    data = {"type": "final", "answer": "done"}
    assert agent.normalize_parsed(data) == [data]


def test_collect_actions_returns_pending():
    data = [{"type": "action", "name": "get_weather", "input": "Warsaw"}]
    pending, final = agent.collect_actions(data, set())
    assert pending == [{"name": "get_weather", "input": "Warsaw"}]
    assert final is None


def test_collect_actions_returns_final():
    data = {"type": "final", "answer": "done"}
    pending, final = agent.collect_actions(data, set())
    assert pending == []
    assert final == "done"


def test_collect_actions_skips_used_tools():
    data = [{"type": "action", "name": "get_weather", "input": "Warsaw"}]
    used = {("get_weather", "Warsaw")}
    pending, final = agent.collect_actions(data, used)
    assert pending == []
    assert final is None


def test_agent_runs_tools_and_returns_final():
    responses = [
        json.dumps([{"type": "action", "name": "get_weather", "input": "Warsaw"}]),
        json.dumps({"type": "final", "answer": "done"}),
    ]

    def fake_call_llm(prompt):
        return responses.pop(0)

    answer = agent.agent("weather?", fake_call_llm)
    assert answer == "done"


def test_agent_retries_after_tool_error(monkeypatch):
    def broken_run(_input):
        raise ValueError("bad expr")

    monkeypatch.setitem(agent.TOOLS, "calculate", broken_run)

    responses = [
        json.dumps([{"type": "action", "name": "calculate", "input": "bad"}]),
        json.dumps([{"type": "action", "name": "calculate", "input": "2+2"}]),
        json.dumps({"type": "final", "answer": "4"}),
    ]

    def fake_call_llm(prompt):
        return responses.pop(0)

    monkeypatch.setattr(agent, "call_llm", fake_call_llm)
    answer = agent.agent("calc?", fake_call_llm)
    assert answer == "4"
