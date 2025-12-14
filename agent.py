import importlib.util
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from openai import OpenAI
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

TOOLS = {}
TOOL_PATHS = {}
tools_lock = threading.Lock()

MAX_TOOL_RETRIES = 3
system_prompt = ""


def is_tool_file(path):
    basename = os.path.basename(path)
    return path.endswith(".py") and not basename.startswith("_")


def refresh_system_prompt():
    global system_prompt
    system_prompt = build_system_prompt()


def load_tool(path):
    path = os.path.abspath(path)
    if not is_tool_file(path):
        return

    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "run"), "Tool missing run()"
    assert hasattr(module, "tool_name"), "Tool missing tool_name"

    with tools_lock:
        old_name = TOOL_PATHS.get(path)
        if old_name and old_name != module.tool_name:
            TOOLS.pop(old_name, None)

        TOOLS[module.tool_name] = module.run
        TOOL_PATHS[path] = module.tool_name

    refresh_system_prompt()
    print(f"[tools] reloaded {module.tool_name} from {path}")


def unload_tool(path):
    path = os.path.abspath(path)
    if not is_tool_file(path):
        return

    with tools_lock:
        tool_name = TOOL_PATHS.pop(path, None)
        if tool_name:
            TOOLS.pop(tool_name, None)

    refresh_system_prompt()
    if tool_name:
        print(f"[tools] unloaded {tool_name} ({path})")


def load_tools(folder="tools"):
    with tools_lock:
        TOOLS.clear()
        TOOL_PATHS.clear()

    for file in os.listdir(folder):
        if not file.endswith(".py") or file.startswith("_"):
            continue
        load_tool(os.path.join(folder, file))


def build_system_prompt():
    with tools_lock:
        tool_names = sorted(TOOLS)

    tools_list = "\n".join(f"- {name}(input)" for name in tool_names)
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


class ToolReloadHandler(FileSystemEventHandler):
    def __init__(self):
        self._timers = {}
        self._timers_lock = threading.Lock()

    def _schedule(self, path, action):
        path = os.path.abspath(path)

        with self._timers_lock:
            timer = self._timers.pop(path, None)
            if timer:
                timer.cancel()
            self._timers[path] = threading.Timer(
                0.3,
                self._handle,
                args=(path, action),
            )
            self._timers[path].start()

    def _handle(self, path, action):
        with self._timers_lock:
            self._timers.pop(path, None)

        if not is_tool_file(path):
            return

        try:
            if action == "load":
                load_tool(path)
            elif action == "unload":
                unload_tool(path)
        except Exception as e:
            print(f"[tools] reload failed for {path}: {e}")

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule(event.src_path, "load")

    def on_created(self, event):
        if not event.is_directory:
            self._schedule(event.src_path, "load")

    def on_deleted(self, event):
        if not event.is_directory:
            self._handle(event.src_path, "unload")

    def on_moved(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path, "unload")
        self._schedule(event.dest_path, "load")


def start_tool_watcher(folder="tools"):
    observer = Observer()
    observer.schedule(ToolReloadHandler(), folder, recursive=False)
    observer.daemon = True
    observer.start()
    return observer


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
        with tools_lock:
            fn = TOOLS[action["name"]]
        return action["name"], action["input"], fn(action["input"])

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


load_tools()
refresh_system_prompt()
start_tool_watcher()

print(agent("Check the weeather in Warsaw, show latest AI news, and how much is 15 × 32?", call_llm))
