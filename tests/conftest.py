import pytest

import agent


@pytest.fixture(autouse=True)
def reset_tools():
    agent.TOOLS.clear()
    agent.TOOL_PATHS.clear()
    agent.system_prompt = ""
    agent.load_tools()
    agent.refresh_system_prompt()
    yield
