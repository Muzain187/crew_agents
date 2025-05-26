from crewai import Agent, Crew, Process, Task, TaskOutput,LLM
from crewai.project import CrewBase, agent, crew, task,before_kickoff, after_kickoff
from crewai_tools import FileReadTool,DirectorySearchTool,DirectoryReadTool,CSVSearchTool
import file_crew.utils as ut
from file_crew.models import *
from file_crew.tools.custom_tool import CSVMetadataTool
from file_crew.tools.recon_tool import ReconIDGeneratorTool
from file_crew.tools.task_exec_tool import ProcessRequestTool
from file_crew.utils.agents.data_agent_bot.process import process_request


# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators
meta_tool = CSVMetadataTool()
recon_tool = ReconIDGeneratorTool()
process_tool = ProcessRequestTool()

llm = LLM(
    model="gemini/gemini-1.5-flash-002",
    temperature=0.5,
    api_key="AIzaSyBolwbznjaVGHeB6bl_fwzWUvlK6KvgWqU"
)
print("LLM =>",llm)
# file_tool = FileReadTool(file_path="D:\\AI_agents\\file_crew\\src\\file_crew\\payload_dataset.csv")
file_read_tool = FileReadTool()
source_extractor_file = FileReadTool("D:\\AI_AGENTS\\crew_agents\\src\\file_crew\\output_files\\source_extractor.txt")
csv_tool = CSVSearchTool(
    config=dict(
        llm=dict(
            provider="google", # Options include ollama, google, anthropic, llama2, and more
            config=dict(
                model="gemini-1.5-flash",
                # Additional configurations here
            ),
        ),
        embedder=dict(
            provider="google", # or openai, ollama, ...
            config=dict(
                model="models/embedding-001",
                task_type="retrieval_document",
                # title="Embeddings",
            ),
        ),
        )
    )
directory_search_tool = DirectoryReadTool(
    "D:\\AI_AGENTS\\crew_agents\\src\\file_crew\\uploaded_files",
    config=dict(
        llm=dict(
            provider="google", # Options include ollama, google, anthropic, llama2, and more
            config=dict(
                model="gemini-1.5-flash",
                # Additional configurations here
            ),
        ),
        embedder=dict(
            provider="google", # or openai, ollama, ...
            config=dict(
                model="models/embedding-001",
                task_type="retrieval_document",
                # title="Embeddings",
            ),
        ),
    )                                        
    )

directory_search_tool2 = DirectoryReadTool(
    "D:\\AI_AGENTS\\crew_agents\\src\\file_crew\\output_files",
    config=dict(
        llm=dict(
            provider="google", # Options include ollama, google, anthropic, llama2, and more
            config=dict(
                model="gemini-1.5-flash",
                # Additional configurations here
            ),
        ),
        embedder=dict(
            provider="google", # or openai, ollama, ...
            config=dict(
                model="models/embedding-001",
                task_type="retrieval_document",
                # title="Embeddings",
            ),
        ),
    )                                        
    )
agent_output_list = []
agent2_output_list = []

def callback_function(output: TaskOutput):
    # Do something after the task is completed
    # Example: Send an email to the manager

    global agent_output_list
    agent_output_list.append(output.raw)
    
    

@CrewBase
class FileCrew():
    """FileCrew crew"""
    @after_kickoff
    def after_kickoff_function(self, result):
        print(f"After kickoff function with result:")
        global agent2_output_list
        for instruction in agent_output_list:
            print("Executing instruction:\n",instruction)
            result = process_request(instruction)
            agent2_output_list.append(result)

        print("All instructions are executed successfully..")
        return result 

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
            tools=[directory_search_tool,file_read_tool],
            max_rpm=10,
            llm=llm,            
            # allow_code_execution=True,
            # code_execution_mode="unsafe",
            verbose=True
        )
    
    @agent
    def source_executor(self) -> Agent:
        return Agent(
            config=self.agents_config['source_executor'],
            max_rpm=10,
            allow_delegation=True,
            # llm=LLM(model="gemini-1.5-flash", temperature=0.5,api_key="AIzaSyBolwbznjaVGHeB6bl_fwzWUvlK6KvgWqU"),
            # allow_code_execution=True,
            # code_execution_mode="unsafe",
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def source_extractor(self) -> Task:
        return Task(
            config=self.tasks_config['source_extractor'],
            callback=callback_function,
            tools=[directory_search_tool],
            allow_delegation=True,
            output_file="src\\file_crew\\output_files\\source_extractor.txt",
            # output_json=EntitiesContainer,
            # callback=ut.call_endpoint,
            human_input=True
        )
    
    @task
    def source_fields_extractor(self) -> Task:
        return Task(
            config=self.tasks_config['source_fields_extractor'],
            context=[self.source_extractor()],
            # output_json=EntitiesContainer,
            # callback=ut.call_endpoint,
            callback=callback_function,
            output_file="src\\file_crew\\output_files\\source_fields_extractor.txt",
            human_input=True

        )
    
    @task
    def recon_creator(self) -> Task:
        return Task(
            config=self.tasks_config['recon_creator'],
            tools=[recon_tool],
            callback=callback_function,
            output_file="src\\file_crew\\output_files\\recon_creator.txt",
            # context=[self.source_extractor()],
            # output_json=EntitiesContainer,
            # callback=ut.call_endpoint,
            human_input=True
        )
    
    @task
    def recon_field_creator(self) -> Task:
        return Task(
            config=self.tasks_config['recon_field_creator'],
            context=[self.recon_creator(),self.source_fields_extractor()],
            callback=callback_function,
            output_file="src\\file_crew\\output_files\\recon_field_creator.txt",
            human_input=True
        )
    @task
    def recon_field_summay(self) -> Task:
        return Task(
            config=self.tasks_config['recon_field_summay'],
            context=[self.recon_creator(),self.recon_field_creator()],
            callback=callback_function,
            output_file="src\\file_crew\\output_files\\recon_field_summay.txt",
            human_input=True
        )
    
    @task
    def map_source_recon(self) -> Task:
        return Task(
            config=self.tasks_config['map_source_recon'],
            context=[self.source_extractor(),self.recon_creator()],
            callback=callback_function,
            output_file="src\\file_crew\\output_files\\map_source_recon.txt",
            human_input=True
        )
    
    @task
    def matching_rule(self) -> Task:
        return Task(
            config=self.tasks_config['matching_rule'],
            context=[self.recon_creator()],
            callback=callback_function,
            output_file="src\\file_crew\\output_files\\matching_rule.txt",
            human_input=True
        )
    @task
    def event_creation(self) -> Task:
        return Task(
            config=self.tasks_config['event_creation'],
            context=[self.recon_creator()],
            callback=callback_function,
            output_file="src\\file_crew\\output_files\\event_creation.txt",
            human_input=True
        )

    # @task
    # def task_executor_1(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['task_executor_1'],
    #         context=[self.source_extractor()],
    #         tools=[process_tool],
    #         human_input=True
    #     )
    # @task
    # def task_executor_2(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['task_executor_2'],
    #         context=[self.source_fields_extractor()],
    #         tools=[process_tool],
    #         human_input=True

    #     )
    # @task
    # def task_executor_3(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['task_executor_3'],
    #         context=[self.recon_creator()],
    #         tools=[process_tool],
    #         human_input=True


    #     )
    # @task
    # def task_executor_4(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['task_executor_4'],
    #         context=[self.recon_field_creator()],
    #         tools=[process_tool],
    #         human_input=True


    #     )
    # @task
    # def task_executor_5(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['task_executor_5'],
    #         context=[self.recon_field_summay()],
    #         tools=[process_tool],
    #         human_input=True


    #     )
    # @task
    # def task_executor_6(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['task_executor_6'],
    #         context=[self.map_source_recon()],
    #         tools=[process_tool],
    #         human_input=True


    #     )
    # @task
    # def task_executor_7(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['task_executor_7'],
    #         context=[self.matching_rule()],
    #         tools=[process_tool],
    #         human_input=True


    #     )
    # @task
    # def task_executor_8(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['task_executor_8'],
    #         context=[self.event_creation()],
    #         tools=[process_tool],
    #         human_input=True


    #     )


    @crew
    def crew(self) -> Crew:
        """Creates the FileCrew crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            # verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
    
    

