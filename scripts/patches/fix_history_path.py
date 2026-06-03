import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

# Fix the loadHistory path
old_js = "const history = await api('/api/sessions');"
new_js = "const history = await api('/api/sessions/history');"

code = code.replace(old_js, new_js)

with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Fixed loadHistory endpoint.")
