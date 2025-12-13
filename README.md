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

## langchain-agent.py


memory []
----------------------------
memory [{'tool': 'get_weather', 'input': 'Wrocław', 'output': 'Weather in Wrocław: rainy 18°C'}]
Tak, potrzebujesz parasola we Wrocławiu (jest deszczowo). 15 * 32 = 480.
