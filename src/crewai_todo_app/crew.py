import os

from dotenv import load_dotenv

load_dotenv(override=True)
os.environ.setdefault("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENAI_MODEL_NAME", "openrouter/owl-alpha")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
if os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = os.environ["OPENAI_API_KEY"]
if os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
if os.environ.get("OPENAI_API_BASE"):
    os.environ["OPENROUTER_API_BASE"] = os.environ["OPENAI_API_BASE"]
if os.environ.get("OPENROUTER_API_BASE") and not os.environ.get("OPENAI_API_BASE"):
    os.environ["OPENAI_API_BASE"] = os.environ["OPENROUTER_API_BASE"]

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

@CrewBase
class CrewAIDroneChecklistApp:
    """CrewAI drone checklist crew."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def operations_planner(self) -> Agent:
        return Agent(config=self.agents_config["operations_planner"], verbose=True)

    @agent
    def safety_designer(self) -> Agent:
        return Agent(config=self.agents_config["safety_designer"], verbose=True)

    @agent
    def ui_designer(self) -> Agent:
        return Agent(config=self.agents_config["ui_designer"], verbose=True)

    @agent
    def full_stack_developer(self) -> Agent:
        return Agent(config=self.agents_config["full_stack_developer"], verbose=True)

    @agent
    def qa_tester(self) -> Agent:
        return Agent(config=self.agents_config["qa_tester"], verbose=True)

    @task
    def plan_operations_task(self) -> Task:
        return Task(config=self.tasks_config["plan_operations_task"])

    @task
    def design_safety_task(self) -> Task:
        return Task(config=self.tasks_config["design_safety_task"])

    @task
    def design_ui_task(self) -> Task:
        return Task(config=self.tasks_config["design_ui_task"])

    @task
    def develop_application_task(self) -> Task:
        return Task(config=self.tasks_config["develop_application_task"], output_file="generated_drone_app.py")

    @task
    def qa_review_task(self) -> Task:
        return Task(config=self.tasks_config["qa_review_task"], output_file="generated_drone_app_qa.py")

    @crew
    def crew(self) -> Crew:
        """Creates the CrewAI drone checklist crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
