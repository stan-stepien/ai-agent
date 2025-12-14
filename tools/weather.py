class WeatherTool:
    name = "get_weather"

    def run(self, input: str) -> str:
        return f"Weather in {input}: rainy 18°C"


tool = WeatherTool()
tool_name = tool.name
run = tool.run
