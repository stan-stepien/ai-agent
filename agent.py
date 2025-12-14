import importlib.util
import json
import os
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from openai import OpenAI

TOOLS = {}

MAX_TOOL_RETRIES = 3


def load_tools(folder="tools"):
    for file in os.listdir(folder):
        if not file.endswith(".py") or file.startswith("_"):
            continue

        name = file[:-3]
        path = os.path.join(folder, file)

        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "run"), "Tool missing run()"
        assert hasattr(module, "tool_name"), "Tool missing tool_name"

        TOOLS[module.tool_name] = module.run


def build_system_prompt():
    tools_list = "\n".join(f"- {name}(input)" for name in sorted(TOOLS))
    return f"""
You are an agent.

You MUST output ONLY JSON array

if action:
[
  {{
    "type": "action",
    "name": "...",
    "input": "..."
  }}
]

If final:
{{
  "type": "final",
  "answer": "..."
}}

Available tools:
{tools_list}
"""


load_tools()
system_prompt = build_system_prompt()


def parse(response):
    print(response)
    return json.loads(response)


def normalize_parsed(data):
    if isinstance(data, dict):
        return [data]
    return data


def collect_actions(data, used_tools):
    pending_actions = []
    for item in normalize_parsed(data):
        if item["type"] == "final":
            return pending_actions, item["answer"]

        name = item["name"]
        tool_input = item["input"]

        if (name, tool_input) in used_tools:
            continue

        pending_actions.append({"name": name, "input": tool_input})

    return pending_actions, None


def run_tools(actions):
    def run_action(action):
        return action["name"], action["input"], TOOLS[action["name"]](action["input"])

    with ThreadPoolExecutor() as executor:
        return list(executor.map(run_action, actions))


def agent(question, call_llm):
    memory = []
    used_tools = set()

    while True:
        print('----------------------------')
        print(memory)

        prompt = system_prompt + "\n\nQuestion: " + question + "\n\nMemory:\n" + str(memory)

        response = call_llm(prompt)
        data = parse(response)
        pending_actions, final_answer = collect_actions(data, used_tools)
        if final_answer is not None:
            return final_answer

        if pending_actions:
            for attempt in range(MAX_TOOL_RETRIES):
                try:
                    results = run_tools(pending_actions)
                    for name, tool_input, result in results:
                        used_tools.add((name, tool_input))
                        memory.append({
                            "tool": name,
                            "input": tool_input,
                            "output": result
                        })
                    break
                except Exception as e:
                    if attempt == MAX_TOOL_RETRIES - 1:
                        memory.append({"error": str(e), "actions": pending_actions})
                        break
                    response = llm_fix(response, str(e))
                    data = parse(response)
                    pending_actions, final_answer = collect_actions(data, used_tools)
                    if final_answer is not None:
                        return final_answer
                    if not pending_actions:
                        break


def llm_fix(response, error):
    prompt = f"""
The tool call failed.

Original response:
{response}

Error:
{error}

Return ONLY corrected JSON (same format as original: action array or final object).
"""

    return call_llm(prompt)


def call_llm(prompt: str):
    load_dotenv()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = openai_client.chat.completions.create(
        # model="gpt-4o-mini",
        model="gpt-5.4-nano",
        messages=[
            # {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


print(agent("Check the weeather in Warsaw, show latest AI news, and how much is 15 × 32?", call_llm))
