from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileReadTool
import file_crew.utils as ut
from file_crew.models import *

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

file_tool = FileReadTool(file_path="D:\\AI_agents\\file_crew\\src\\file_crew\\payload_dataset.csv")



@CrewBase
class FileCrew():
    """FileCrew crew"""

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def source_fields(self) -> Agent:
        return Agent(
            config=self.agents_config['source_fields'],
            tools=[file_tool],
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def source_extractor(self) -> Task:
        return Task(
            config=self.tasks_config['source_extractor'],
            output_json=EntitiesContainer,
            callback=ut.call_endpoint,
            human_input=True
        )
    
    @task
    def source_fields_extractor(self) -> Task:
        return Task(
            config=self.tasks_config['source_fields_extractor'],
            context=[self.source_extractor()],
            output_json=EntitiesContainer,
            callback=ut.call_endpoint,
            human_input=True
        )


    @crew
    def crew(self) -> Crew:
        """Creates the FileCrew crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
