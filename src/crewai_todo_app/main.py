#!/usr/bin/env python
import os
import sys
import warnings

from dotenv import load_dotenv

load_dotenv(override=True)
os.environ.setdefault("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENAI_MODEL_NAME", "openrouter/owl-alpha")
if os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = os.environ["OPENAI_API_KEY"]
if os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
if os.environ.get("OPENAI_API_BASE"):
    os.environ["OPENROUTER_API_BASE"] = os.environ["OPENAI_API_BASE"]
if os.environ.get("OPENROUTER_API_BASE") and not os.environ.get("OPENAI_API_BASE"):
    os.environ["OPENAI_API_BASE"] = os.environ["OPENROUTER_API_BASE"]

from crewai_todo_app.crew import CrewAIDroneChecklistApp

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def _default_inputs() -> dict[str, str]:
    return {
        "project_name": "Drone Flight Checklist App",
        "output_file": "drone_checklist_app.py",
    }


def run():
    """Run the crew."""
    inputs = _default_inputs()

    try:
        CrewAIDroneChecklistApp().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """Train the crew for a given number of iterations."""
    inputs = _default_inputs()

    try:
        CrewAIDroneChecklistApp().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """Replay the crew execution from a specific task."""
    try:
        CrewAIDroneChecklistApp().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """Test the crew execution and return the results."""
    inputs = _default_inputs()

    try:
        CrewAIDroneChecklistApp().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


def run_with_trigger():
    """Run the crew with trigger payload."""
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = _default_inputs()
    inputs["crewai_trigger_payload"] = trigger_payload

    try:
        result = CrewAIDroneChecklistApp().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
