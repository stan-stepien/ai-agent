class NewsTool:
    name = "get_news"

    def run(self, input: str) -> str:
        return f"News about {input}: AI adoption growing"


tool = NewsTool()
tool_name = tool.name
run = tool.run
