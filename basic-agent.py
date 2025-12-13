# tools (API simulation)

def get_weather(city: str):
    return f"Weather in {city}: sunny, 22°C"

def get_news(topic: str):
    return f"Latest news about {topic}: AI is growing fast."

def calculate(expression: str):
    try:
        return str(eval(expression))
    except:
        return "Invalid expression"

# system prompt with multi-tool ReAct (Reason + Act)
system_prompt = """
You run in a loop of Thought, Action, PAUSE, Action_Response, Answer.

Available actions:

get_weather:
input: city (string)

get_news:
input: topic (string)

calculate:
input: expression (string math)

Rules:
- Decide best action
- Output Action in JSON format:
  {"function_name": "...", "function_parms": {...}}
- After Action_Response, continue reasoning or give Answer
- Never call the same tool twice for the same question.
"""


# action parser
import json

def parse_action(text):
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except:
        return None

# dispatcher
def run_tool(action):
    name = action["function_name"]
    params = action["function_parms"]
    print(f"run tool {name}({params})")

    if name == "get_weather":
        return get_weather(params["city"])

    elif name == "get_news":
        return get_news(params["topic"])

    elif name == "calculate":
        return calculate(params["expression"])

    return "Unknown tool"

# agent loop
def agent(question, call_llm):
    memory = ""
    print('----------------------------')
    while True:
        prompt = system_prompt + "\n\n" + memory + f"\nQuestion: {question}"
        # print(prompt)
        response = call_llm(prompt)
        print(response)

        if "Answer:" in response:
            return response

        action = parse_action(response)

        if action:
            result = run_tool(action)
            print(result)
            # memory += f"\nAction_Response: {result}\n"
            memory += f"\nAction: {action}\nAction_Response: {result}\nTool_used: {action['function_name']}\n"
        else:
            return "Error: no valid action"

from openai import OpenAI
import os
from dotenv import load_dotenv

def call_llm(prompt: str):
    load_dotenv()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = openai_client.chat.completions.create(
        # model="gpt-4o-mini",
        model="gpt-5.4-nano",
        messages=[
            #{"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


agent("Czy potrzebuję parasola we Wroclawiu i ile to 15 * 32?", call_llm)