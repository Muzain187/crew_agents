from crewai.tools import BaseTool
from pydantic import BaseModel
from datetime import datetime
from typing import Type

class ReconIDInput(BaseModel):
    pass  # No input needed

class ReconIDGeneratorTool(BaseTool):
    name: str = "recon_id_generator"
    description: str = "Generate a unique ID starting with 'recon_' followed by the current timestamp"
    args_schema: Type[ReconIDInput] = ReconIDInput

    def _run(self, **kwargs):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_id = f"recon_{timestamp}"
        return {"recon_id": new_id}

    async def _arun(self, **kwargs):
        return self._run(**kwargs)
