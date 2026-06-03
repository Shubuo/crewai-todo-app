import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

# Add OPENROUTER_API_KEY mapping right after load_dotenv() and OPENAI_API_BASE
old_env = """os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"
os.environ["OPENAI_MODEL_NAME"] = "openrouter/owl-alpha"
# OPENAI_API_KEY is assumed to be loaded from .env"""

new_env = """os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"
os.environ["OPENAI_MODEL_NAME"] = "openrouter/owl-alpha"
# OPENAI_API_KEY is assumed to be loaded from .env
# Litellm needs OPENROUTER_API_KEY for openrouter models specifically
if os.environ.get("OPENAI_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = os.environ.get("OPENAI_API_KEY")"""

code = code.replace(old_env, new_env)

with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Applied openrouter key map fix.")
