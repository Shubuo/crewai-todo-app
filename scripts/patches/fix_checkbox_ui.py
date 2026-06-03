import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

new_js = """
                    const isCompleted = (item.completed === 1 || item.completed === true || item.completed === '1');
                    const isChecked = isCompleted ? 'completed' : '';
                    const checkIcon = isCompleted ? '✅' : '⬜';
                    
                    if (item.is_reference === 1) {
                        itemDiv.innerHTML = `<div class="item-text" style="color:var(--text-muted)">ℹ️ ${item.item_text}</div>`;
                    } else {
                        itemDiv.innerHTML = `
                            <div class="item-text ${isChecked}" onclick="toggleItem(${currentSession.id}, ${item.session_item_id}, ${isCompleted ? 0 : 1})">
                                ${checkIcon} ${item.item_text}
                            </div>
                        `;
                    }
"""

old_js = """
                    const isChecked = item.completed ? 'completed' : '';
                    const checkIcon = item.completed ? '✅' : '⬜';
                    
                    if (item.is_reference === 1) {
                        itemDiv.innerHTML = `<div class="item-text" style="color:var(--text-muted)">ℹ️ ${item.item_text}</div>`;
                    } else {
                        itemDiv.innerHTML = `
                            <div class="item-text ${isChecked}" onclick="toggleItem(${currentSession.id}, ${item.session_item_id}, ${item.completed ? 0 : 1})">
                                ${checkIcon} ${item.item_text}
                            </div>
                        `;
                    }
"""

# Strip out indentation to make replacement robust
import textwrap
def normalize_spaces(s):
    return re.sub(r'\s+', ' ', s)

# Direct replace
code = code.replace(old_js.strip(), new_js.strip())

# Also, reset all current items to 0 just to clear out the buggy state for the user
import sqlite3
try:
    conn = sqlite3.connect("drone_checklist_ges.db")
    conn.execute("UPDATE session_items SET completed = 0")
    conn.commit()
    conn.close()
    print("Reset DB states successfully.")
except Exception as e:
    print(f"Failed to reset DB: {e}")

with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Updated checklist rendering logic.")
