from httpx import options  # tools (API simulation)

def get_weather(city):
    return f"Weather in {city}: rainy 18°C"


def get_news(topic):
    return f"News about {topic}: AI adoption growing"


def calculate(expr):
    return str(eval(expr))

TOOLS = {
    "get_weather": get_weather,
    "get_news": get_news,
    "calculate": calculate
}

MAX_TOOL_RETRIES = 3

# system prompt with multi-tool ReAct (Reason + Act), only JSON output
system_prompt = """
You are an agent.

You MUST output ONLY JSON array

if action:
[
  {
    "type": "action",
    "name": "...",
    "input": "..."
  }
]

If final:
{
  "type": "final",
  "answer": "..."
}

Available tools:
- get_weather(city)
- get_news(topic)
- calculate(expression)
"""

# agent loop
import json

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


from concurrent.futures import ThreadPoolExecutor

# another option to run async functions
#
# results = await asyncio.gather(
#     get_weather("Warsaw"),
#     get_news("AI"),
#     calculate("15*32")
# )
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


from openai import OpenAI
import os
from dotenv import load_dotenv

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

# ----------------------------
# []
# [
#   {
#     "type": "action",
#     "name": "get_weather",
#     "input": "Warsaw"
#   },
#   {
#     "type": "action",
#     "name": "get_news",
#     "input": "AI"
#   },
#   {
#     "type": "action",
#     "name": "calculate",
#     "input": "15 * 32"
#   }
# ]
# ----------------------------
# [{'tool': 'get_weather', 'input': 'Warsaw', 'output': 'Weather in Warsaw: rainy 18°C'}, {'tool': 'get_news', 'input': 'AI', 'output': 'News about AI: AI adoption growing'}, {'tool': 'calculate', 'input': '15 * 32', 'output': '480'}]
# [
#   {
#     "type": "final",
#     "answer": "Weather in Warsaw: rainy 18°C. Latest AI news: AI adoption growing. 15 × 32 = 480."
#   }
# ]
# Weather in Warsaw: rainy 18°C. Latest AI news: AI adoption growing. 15 × 32 = 480.