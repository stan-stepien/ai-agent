# Basic multi-tool agent in python

## Architecture

Tools:
*  get_weather(city)
* get_news(topic)
* calculate(expression)

Loop:
* LLM thinks (Thought)
* select tool (Action)
* agent code executes a function
* function result returns to LLM (Action_Response)
* LLM returns Answer
