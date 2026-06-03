import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

# Fix create_session so it inserts session_items!
new_create = """@app.route('/api/sessions', methods=['POST'])
def create_session():
    db = get_db()
    drone_name = request.json.get('drone_name', 'Bilinmeyen Drone')
    
    # Mevcut aktif session varsa kapat
    db.execute("UPDATE flight_sessions SET status = 'cancelled' WHERE status = 'active'")
    
    start_time = datetime.now().isoformat()
    telemetry = {
        'wind_speed': __import__('random').randint(2, 15),
        'temperature': __import__('random').randint(15, 35),
        'battery': __import__('random').randint(70, 100),
        'gps_satellites': __import__('random').randint(8, 20)
    }
    
    cursor = db.execute(
        'INSERT INTO flight_sessions (start_time, drone_name, status, telemetry_data) VALUES (?, ?, ?, ?)',
        (start_time, drone_name, 'active', __import__('json').dumps(telemetry))
    )
    session_id = cursor.lastrowid
    
    # Fix: Actually insert the checklist items for the new session!
    template_items = db.execute(
        'SELECT id, is_reference FROM template_items ORDER BY section, order_index'
    ).fetchall()
    for item in template_items:
        db.execute(
            'INSERT INTO session_items (session_id, template_item_id, completed) VALUES (?, ?, ?)',
            (session_id, item['id'], 0)
        )
        
    db.commit()
    return jsonify({'id': session_id})"""

code = re.sub(r"@app\.route\('/api/sessions', methods=\['POST'\]\).*?return jsonify\(\{'id': session_id\}\)", new_create, code, flags=re.DOTALL)

with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Fixed create_session to insert items.")
