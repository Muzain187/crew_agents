from crewai.tasks.task_output import TaskOutput
import json
import re


def call_endpoint(output: TaskOutput):
    output_str = output.raw
    output_str = re.sub(r'^```json\s*|\s*```$', '', output_str, flags=re.MULTILINE)

    data = json.loads(output_str)
    print(json.dumps(data, indent=2))
