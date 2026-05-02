import os
import sqlite3
from pathlib import Path

from flask import Flask, request, jsonify, g, render_template_string

# Configuration
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / 'todo.db'
app = Flask(__name__)

# Database helpers
def get_db():
    """Get database connection for current request context."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def row_to_todo(row):
    """Convert a SQLite row into the API shape expected by the UI."""
    return {
        'id': row['id'],
        'title': row['title'],
        'completed': bool(row['completed']),
        'created_at': row['created_at'],
    }


def get_json_payload():
    """Return a JSON object payload or None when the request body is invalid."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def fetch_todo_row(todo_id):
    """Fetch a todo row by id."""
    db = get_db()
    return db.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at end of request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with todos table."""
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

# Routes - API
@app.route('/api/todos', methods=['GET'])
def get_todos():
    """Get all todos."""
    db = get_db()
    cursor = db.execute('SELECT * FROM todos ORDER BY created_at DESC')
    todos = [row_to_todo(row) for row in cursor.fetchall()]
    return jsonify(todos)

@app.route('/api/todos', methods=['POST'])
def create_todo():
    """Create a new todo."""
    data = get_json_payload()
    if data is None:
        return jsonify({'error': 'A JSON object is required'}), 400

    title = data.get('title', '').strip()

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    db = get_db()
    cursor = db.execute(
        'INSERT INTO todos (title, completed) VALUES (?, ?)',
        (title, 0)
    )
    db.commit()

    todo_id = cursor.lastrowid
    todo = row_to_todo(fetch_todo_row(todo_id))

    return jsonify(todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['GET'])
def get_todo(todo_id):
    """Get a specific todo by ID."""
    todo = fetch_todo_row(todo_id)

    if todo is None:
        return jsonify({'error': 'Todo not found'}), 404

    return jsonify(row_to_todo(todo))

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    """Update a todo (title and/or completed status)."""
    data = get_json_payload()
    if data is None:
        return jsonify({'error': 'A JSON object is required'}), 400

    todo = fetch_todo_row(todo_id)

    if todo is None:
        return jsonify({'error': 'Todo not found'}), 404

    title = data.get('title', todo['title'])
    if title is not None:
        title = title.strip()
        if not title:
            return jsonify({'error': 'Title cannot be empty'}), 400

    completed = data.get('completed', bool(todo['completed']))
    if not isinstance(completed, bool):
        return jsonify({'error': 'Completed must be true or false'}), 400

    db = get_db()
    db.execute(
        'UPDATE todos SET title = ?, completed = ? WHERE id = ?',
        (title, 1 if completed else 0, todo_id)
    )
    db.commit()

    updated_todo = row_to_todo(fetch_todo_row(todo_id))

    return jsonify(updated_todo)

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    """Delete a todo."""
    db = get_db()
    todo = fetch_todo_row(todo_id)

    if todo is None:
        return jsonify({'error': 'Todo not found'}), 404

    db.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
    db.commit()

    return jsonify({'message': 'Todo deleted successfully'})

# Routes - UI
@app.route('/')
def index():
    """Render the main todo application page."""
    return render_template_string(TEMPLATE)

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Flask Todo App</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: #f0f2f5;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #1a1a2e;
            margin-bottom: 30px;
            font-size: 2.5rem;
        }
        .todo-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .input-section {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            gap: 10px;
        }
        #todo-input {
            flex: 1;
            padding: 12px 16px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            outline: none;
        }
        #todo-input:focus {
            box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.3);
        }
        .btn-add {
            padding: 12px 24px;
            background: #1a1a2e;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, background 0.2s;
        }
        .btn-add:hover {
            background: #2d2d44;
            transform: scale(1.02);
        }
        .error-message {
            background: #fee2e2;
            color: #dc2626;
            padding: 12px 20px;
            margin: 0;
            display: none;
        }
        .error-message.show {
            display: block;
        }
        .todo-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .todo-item {
            display: flex;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid #e5e7eb;
            transition: background 0.2s;
        }
        .todo-item:last-child {
            border-bottom: none;
        }
        .todo-item:hover {
            background: #f9fafb;
        }
        .todo-item.completed .todo-text {
            text-decoration: line-through;
            color: #9ca3af;
        }
        .todo-checkbox {
            width: 22px;
            height: 22px;
            margin-right: 16px;
            cursor: pointer;
            accent-color: #667eea;
        }
        .todo-text {
            flex: 1;
            font-size: 16px;
            color: #374151;
            word-break: break-word;
        }
        .todo-meta {
            display: block;
            margin-top: 4px;
            font-size: 12px;
            color: #9ca3af;
        }
        .edit-input {
            flex: 1;
            padding: 8px 12px;
            font-size: 16px;
            border: 2px solid #667eea;
            border-radius: 6px;
            outline: none;
        }
        .btn-group {
            display: flex;
            gap: 8px;
            margin-left: 12px;
        }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.2s;
        }
        .btn:hover {
            transform: scale(1.05);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-edit {
            background: #e0e7ff;
            color: #4338ca;
        }
        .btn-edit:hover {
            background: #c7d2fe;
        }
        .btn-save {
            background: #d1fae5;
            color: #059669;
        }
        .btn-save:hover {
            background: #a7f3d0;
        }
        .btn-cancel {
            background: #f3f4f6;
            color: #6b7280;
        }
        .btn-cancel:hover {
            background: #e5e7eb;
        }
        .btn-delete {
            background: #fee2e2;
            color: #dc2626;
        }
        .btn-delete:hover {
            background: #fecaca;
        }
        .empty-state {
            padding: 60px 20px;
            text-align: center;
            color: #9ca3af;
        }
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        .empty-state-text {
            font-size: 18px;
        }
        .stats {
            display: flex;
            justify-content: space-between;
            padding: 12px 20px;
            background: #f9fafb;
            border-top: 1px solid #e5e7eb;
            font-size: 14px;
            color: #6b7280;
        }
        .stats span {
            display: flex;
            align-items: center;
            gap: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Todo App</h1>
        <div class="todo-card">
            <div class="input-section">
                <input type="text" id="todo-input" placeholder="What needs to be done?" autocomplete="off">
                <button class="btn-add" onclick="createTodo()">Add</button>
            </div>
            <div id="error-message" class="error-message"></div>
            <ul id="todo-list" class="todo-list"></ul>
            <div id="stats" class="stats"></div>
        </div>
    </div>

    <script>
        const API_URL = '/api/todos';
        
        // Fetch and display all todos
        async function fetchTodos() {
            try {
                const response = await fetch(API_URL);
                if (!response.ok) throw new Error('Failed to fetch');
                const todos = await response.json();
                renderTodos(todos);
                updateStats(todos);
            } catch (error) {
                showError('Failed to load todos. Please refresh the page.');
                console.error('Fetch error:', error);
            }
        }
        
        // Create a new todo
        async function createTodo() {
            const input = document.getElementById('todo-input');
            const title = input.value.trim();
            
            if (!title) {
                showError('Please enter a todo title');
                input.focus();
                return;
            }
            
            hideError();
            
            try {
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to create todo');
                }
                
                input.value = '';
                await fetchTodos();
            } catch (error) {
                showError(error.message);
            }
        }
        
        // Toggle todo completion
        async function toggleTodo(id, currentCompleted) {
            try {
                const response = await fetch(`${API_URL}/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ completed: !currentCompleted })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to update todo');
                }
                
                await fetchTodos();
            } catch (error) {
                showError(error.message);
            }
        }
        
        // Delete a todo
        async function deleteTodo(id) {
            if (!confirm('Are you sure you want to delete this todo?')) {
                return;
            }
            
            try {
                const response = await fetch(`${API_URL}/${id}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to delete todo');
                }
                
                await fetchTodos();
            } catch (error) {
                showError(error.message);
            }
        }
        
        // Start editing a todo
        function startEdit(id, title) {
            const list = document.getElementById('todo-list');
            const item = list.querySelector(`[data-id="${id}"]`);
            
            if (!item) return;
            
            item.innerHTML = `
                <input type="checkbox" class="todo-checkbox" disabled>
                <input type="text" class="edit-input" id="edit-${id}" value="${escapeHtml(title)}">
                <div class="btn-group">
                    <button class="btn btn-save" onclick="saveEdit(${id})">Save</button>
                    <button class="btn btn-cancel" onclick="fetchTodos()">Cancel</button>
                </div>
            `;
            
            const editInput = document.getElementById(`edit-${id}`);
            editInput.focus();
            editInput.select();
            
            editInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') saveEdit(id);
                if (e.key === 'Escape') fetchTodos();
            });
        }
        
        // Save edited todo
        async function saveEdit(id) {
            const input = document.getElementById(`edit-${id}`);
            const title = input.value.trim();
            
            if (!title) {
                showError('Title cannot be empty');
                input.focus();
                return;
            }
            
            hideError();
            
            try {
                const response = await fetch(`${API_URL}/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to update todo');
                }
                
                await fetchTodos();
            } catch (error) {
                showError(error.message);
            }
        }
        
        // Render todos to the page
        function renderTodos(todos) {
            const list = document.getElementById('todo-list');
            
            if (todos.length === 0) {
                list.innerHTML = `
                    <li class="empty-state">
                        <div class="empty-state-icon">📝</div>
                        <div class="empty-state-text">No todos yet. Add one above!</div>
                    </li>
                `;
                return;
            }
            
            list.innerHTML = todos.map(todo => `
                <li class="todo-item ${todo.completed ? 'completed' : ''}" data-id="${todo.id}">
                    <input type="checkbox" class="todo-checkbox" 
                           ${todo.completed ? 'checked' : ''} 
                           onchange="toggleTodo(${todo.id}, ${todo.completed})">
                    <span class="todo-text">
                        ${escapeHtml(todo.title)}
                        <span class="todo-meta">Created: ${formatDate(todo.created_at)}</span>
                    </span>
                    <div class="btn-group">
                        <button class="btn btn-edit" onclick="startEdit(${todo.id}, '${escapeHtml(todo.title)}')">Edit</button>
                        <button class="btn btn-delete" onclick="deleteTodo(${todo.id})">Delete</button>
                    </div>
                </li>
            `).join('');
        }
        
        // Update statistics
        function updateStats(todos) {
            const total = todos.length;
            const completed = todos.filter(t => t.completed).length;
            const pending = total - completed;
            
            const stats = document.getElementById('stats');
            stats.innerHTML = `
                <span>📊 Total: ${total}</span>
                <span>✅ Completed: ${completed}</span>
                <span>⏳ Pending: ${pending}</span>
            `;
        }

        function formatDate(value) {
            const parsed = new Date(value.replace(' ', 'T'));
            if (Number.isNaN(parsed.getTime())) {
                return value;
            }

            return parsed.toLocaleString();
        }
        
        // Show error message
        function showError(message) {
            const errorDiv = document.getElementById('error-message');
            errorDiv.textContent = message;
            errorDiv.classList.add('show');
            
            setTimeout(() => {
                errorDiv.classList.remove('show');
            }, 5000);
        }
        
        // Hide error message
        function hideError() {
            const errorDiv = document.getElementById('error-message');
            errorDiv.classList.remove('show');
        }
        
        // Escape HTML to prevent XSS
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML
                .replace(/'/g, '&#39;')
                .replace(/"/g, '&#34;');
        }
        
        // Handle Enter key in input
        document.getElementById('todo-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                createTodo();
            }
        });
        
        // Initial load
        fetchTodos();
    </script>
</body>
</html>
'''

# Initialize database on startup
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))
