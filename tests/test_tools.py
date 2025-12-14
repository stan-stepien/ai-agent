import textwrap

import agent


def test_load_tool_registers_tool():
    path = next(path for path, name in agent.TOOL_PATHS.items() if name == "get_weather")
    result = agent.TOOLS["get_weather"]("Warsaw")
    assert "Warsaw" in result
    assert agent.TOOL_PATHS[path] == "get_weather"


def test_load_tool_picks_up_file_changes(tmp_path):
    tool_file = tmp_path / "demo.py"
    tool_file.write_text(textwrap.dedent("""
        class DemoTool:
            name = "demo_tool"

            def run(self, input: str) -> str:
                return f"v1:{input}"

        tool = DemoTool()
        tool_name = tool.name
        run = tool.run
    """), encoding="utf-8")

    agent.load_tool(tool_file)
    assert agent.TOOLS["demo_tool"]("x") == "v1:x"

    tool_file.write_text(textwrap.dedent("""
        class DemoTool:
            name = "demo_tool"

            def run(self, input: str) -> str:
                return f"v2:{input}"

        tool = DemoTool()
        tool_name = tool.name
        run = tool.run
    """), encoding="utf-8")

    agent.load_tool(tool_file)
    assert agent.TOOLS["demo_tool"]("x") == "v2:x"


def test_unload_tool_removes_tool():
    path = next(path for path, name in agent.TOOL_PATHS.items() if name == "get_weather")
    agent.unload_tool(path)
    assert "get_weather" not in agent.TOOLS
    assert path not in agent.TOOL_PATHS
    assert "get_weather" not in agent.build_system_prompt()


def test_reload_handler_load_and_unload(tmp_path):
    tool_file = tmp_path / "demo.py"
    tool_file.write_text(textwrap.dedent("""
        class DemoTool:
            name = "demo_tool"

            def run(self, input: str) -> str:
                return input

        tool = DemoTool()
        tool_name = tool.name
        run = tool.run
    """), encoding="utf-8")

    handler = agent.ToolReloadHandler()
    handler._handle(str(tool_file), "load")
    assert agent.TOOLS["demo_tool"]("ok") == "ok"

    handler._handle(str(tool_file), "unload")
    assert "demo_tool" not in agent.TOOLS


def test_build_system_prompt_lists_tools():
    prompt = agent.build_system_prompt()
    assert "- calculate(input)" in prompt
    assert "- get_news(input)" in prompt
    assert "- get_weather(input)" in prompt
