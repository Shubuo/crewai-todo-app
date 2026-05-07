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
    def full_stack_developer(self) -> Agent:
        return Agent(
            config=self.agents_config["full_stack_developer"],  # type: ignore[index]
            verbose=True
        )

    @task
    def generate_drone_checklist_app_task(self) -> Task:
        return Task(
            config=self.tasks_config["generate_drone_checklist_app_task"],  # type: ignore[index]
            output_file="drone_checklist_app.py"
        )

    @crew
    def crew(self) -> Crew:
        """Creates the CrewAI drone checklist crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
