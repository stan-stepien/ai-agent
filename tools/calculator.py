class CalculatorTool:
    name = "calculate"

    def run(self, input: str) -> str:
        return str(eval(input))


tool = CalculatorTool()
tool_name = tool.name
run = tool.run
