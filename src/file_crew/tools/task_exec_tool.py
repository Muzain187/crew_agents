from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from file_crew.utils.agents.data_agent_bot.process import process_request

class ProcessRequestInput(BaseModel):
    user_input: str = Field(..., description="Input string to process using the function")

class ProcessRequestTool(BaseTool):
    name: str = "process_request_tool"
    description: str = "Process input text using the custom process_request() function"
    args_schema: Type[ProcessRequestInput] = ProcessRequestInput

    def _run(self, user_input: str):
        # result = process_request(user_input)
        # print("Result =>",result)
        result = user_input
        return "Instruction =>"+result

    async def _arun(self, user_input: str):
        return self._run(user_input)
