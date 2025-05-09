from typing import Type, Optional
from pathlib import Path
import pandas as pd
import uuid

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Directory where CSVs are stored (relative to project root)
DATA_DIR = Path(__file__).parent.parent / "uploaded_files"

class CSVMetaInput(BaseModel):
    path: Optional[str] = Field(
        None,
        description=(
            "(Optional) Filename of a CSV in the uploaded_files folder. "
            "If omitted, all .csv files in the directory will be processed."
        )
    )

class CSVMetadataTool(BaseTool):
    name: str = "csv_metadata"
    description: str = (
        "Extract column headers and data types from CSV file(s) stored in the 'uploaded_files' folder. "
        "Provide `path` to select a specific file, or omit to scan all CSVs."
    )
    args_schema: Type[CSVMetaInput] = CSVMetaInput

    def _run(self, **kwargs):
        path = kwargs.get("path")
        results = {}

        # Resolve files
        if path:
            target = DATA_DIR / path
            if not target.is_file():
                raise FileNotFoundError(f"File not found: {target}")
            files = [target]
        else:
            files = list(DATA_DIR.glob("*.csv"))

        if not files:
            raise FileNotFoundError(f"No CSV files found in {DATA_DIR}")

        # Parse each CSV file
        for file_path in files:
            df = pd.read_csv(file_path)
            headers = list(df.columns)
            dtypes = {
                col: self._map_dtype(df[col])
                for col in df.columns
            }
            results[file_path.name] = {
                "headers": headers,
                "dtypes": dtypes,
            }

        return results

    async def _arun(self, **kwargs):
        return self._run(**kwargs)

    def _map_dtype(self, series: pd.Series) -> str:
        dtype = series.dtype

        if pd.api.types.is_bool_dtype(dtype):
            return "BOOLEAN"
        elif pd.api.types.is_numeric_dtype(dtype):
            return "NUMERIC"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return "DATETIME"
        elif pd.api.types.is_string_dtype(dtype):
            try:
                parsed = pd.to_datetime(series, errors='raise')
                if parsed.dt.hour.any() or parsed.dt.minute.any():
                    return "DATETIME"
                else:
                    return "DATE"
            except Exception:
                return "STRING"
        else:
            return "STRING"
