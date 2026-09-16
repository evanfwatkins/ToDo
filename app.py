import random
import re

import dash
from dash import ALL, dcc, html, Input, Output, State, callback
from dash import callback_context as ctx
import pandas as pd
import psycopg
from datetime import datetime
from io import StringIO

try:
    from spellchecker import SpellChecker
except ImportError:
    SpellChecker = None

DB_CONFIG = {
    'dbname': 'todo_app',
    'user': 'todo_app_user',
    'password': 'todo_password',
    'host': 'localhost',
    'port': 5432,
}


def get_db_connection():
    return psycopg.connect(**DB_CONFIG)


def ensure_schema():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'local',
                    task_value TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    note_id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
                    note_value TEXT NOT NULL,
                    completed BOOLEAN NOT NULL DEFAULT FALSE,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
            ''')
            cur.execute('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0')
            cur.execute('ALTER TABLE notes ADD COLUMN IF NOT EXISTS completed BOOLEAN NOT NULL DEFAULT FALSE')
            cur.execute('ALTER TABLE notes ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0')
            cur.execute('UPDATE tasks SET sort_order = task_id WHERE sort_order = 0')
            cur.execute('UPDATE notes SET sort_order = note_id WHERE sort_order = 0')
        conn.commit()


ensure_schema()

# Initialize Dash app
app = dash.Dash(__name__)

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        <style>
            :root {
                --color-dark-slate: #1a2421;
                --color-deep-forest: #1e2925;
                --color-midnight-moss: #243330;
                --color-muted-pine: #3b5249;
                --color-ocean-storm: #435a64;
                --color-misty-teal: #5b7a72;
                --color-spruce-blue: #7ca1a4;
                --color-sage-glint: #90a98f;
                --color-frost-mint: #b6cfc3;
                --color-text-primary: #e4ebe7;
                --color-text-muted: #9bb0a5;
            }

            body {
                margin: 0;
                min-height: 100vh;
                font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
                font-weight: 500;
                background: linear-gradient(180deg, var(--color-dark-slate) 0%, var(--color-deep-forest) 100%);
                color: var(--color-text-primary);
            }

            button,
            input,
            textarea {
                font-family: inherit;
            }

            .todo-app {
                width: min(100%, 1200px);
                min-height: 100vh;
                margin: 0 auto;
                padding: clamp(20px, 4vw, 48px);
                background: rgba(36, 51, 48, 0.92);
                border: 1px solid var(--color-muted-pine);
                border-radius: 0;
                box-shadow: none;
                box-sizing: border-box;
            }

            .todo-input-row {
                display: flex;
                gap: 12px;
                margin-bottom: 22px;
                width: 100%;
            }

            .task-input {
                width: 72%;
                min-width: 0;
                min-height: 52px;
                padding: 13px 14px;
                font-size: clamp(14px, 1.2vw, 16px);
                font-weight: 600;
                line-height: 1.4;
                border: 1px solid var(--color-muted-pine);
                border-radius: 12px;
                background: var(--color-deep-forest);
                color: var(--color-text-primary);
                box-sizing: border-box;
                outline: none;
            }

            .task-input::placeholder {
                color: var(--color-text-muted);
            }

            .task-input:focus {
                border-color: var(--color-spruce-blue);
                box-shadow: 0 0 0 3px rgba(124, 161, 164, 0.24);
            }

            .add-button {
                width: 28%;
                min-width: 140px;
                min-height: 52px;
                padding: 13px 16px;
                border: 1px solid var(--color-muted-pine);
                border-radius: 12px;
                background: linear-gradient(180deg, var(--color-ocean-storm) 0%, var(--color-muted-pine) 100%);
                color: var(--color-text-primary);
                font-weight: 700;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .add-button:hover {
                background: linear-gradient(180deg, var(--color-misty-teal) 0%, var(--color-ocean-storm) 100%);
            }

            .task-table-wrap {
                margin-top: 18px;
                background: var(--color-midnight-moss);
                border: 1px solid var(--color-muted-pine);
                border-radius: 18px;
                overflow: hidden;
                width: 100%;
            }

            .query-panel {
                margin-top: 24px;
                padding: 18px;
                background: var(--color-midnight-moss);
                border: 1px solid var(--color-muted-pine);
                border-radius: 14px;
            }

            .query-panel h2 {
                color: var(--color-text-primary);
                letter-spacing: 0;
            }

            .query-summary {
                padding: 2px 0;
                color: var(--color-text-primary);
                cursor: pointer;
                font-size: 18px;
                font-weight: 700;
                list-style-position: inside;
            }

            .query-panel[open] .query-summary {
                margin-bottom: 16px;
            }

            .query-input {
                width: 100%;
                min-height: 120px;
                padding: 12px;
                resize: vertical;
                box-sizing: border-box;
                border: 1px solid var(--color-muted-pine);
                border-radius: 8px;
                background: var(--color-dark-slate);
                color: var(--color-text-primary);
                font-family: inherit;
                font-size: 14px;
                font-weight: 600;
                line-height: 1.5;
                outline: none;
            }

            .query-input:focus {
                border-color: var(--color-spruce-blue);
                box-shadow: 0 0 0 3px rgba(124, 161, 164, 0.24);
            }

            .query-actions {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-top: 10px;
            }

            .query-button {
                padding: 9px 16px;
                border: 1px solid var(--color-muted-pine);
                border-radius: 8px;
                background: var(--color-sage-glint);
                color: var(--color-dark-slate);
                font-weight: 700;
                cursor: pointer;
            }

            .query-status {
                padding: 7px 10px;
                border: 1px solid var(--color-muted-pine);
                border-radius: 7px;
                color: var(--color-text-primary);
                font-size: 13px;
            }

            .query-results-label {
                margin-top: 18px;
                margin-bottom: 8px;
                color: var(--color-text-muted);
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .query-results {
                margin-top: 14px;
                max-height: 360px;
                overflow: auto;
                border: 1px solid var(--color-muted-pine);
                background: var(--color-dark-slate);
            }

            .query-result-table {
                width: 100%;
                border-collapse: collapse;
                font-family: inherit;
                font-size: 13px;
            }

            .query-result-table th,
            .query-result-table td {
                padding: 8px 10px;
                text-align: left;
                white-space: pre-wrap;
                border-bottom: 1px solid rgba(91, 122, 114, 0.5);
            }

            .query-result-table tbody tr:nth-child(even) {
                background: rgba(91, 122, 114, 0.12);
            }

            .query-result-table th {
                position: sticky;
                top: 0;
                background: var(--color-midnight-moss);
                color: var(--color-text-primary);
                font-family: inherit;
                font-size: 13px;
                font-weight: 700;
            }

            .query-result-table td {
                color: var(--color-text-primary);
            }

            .task-table {
                width: 100%;
                border-collapse: collapse;
                background: var(--color-deep-forest);
            }

            .task-table th {
                padding: 12px 14px;
                text-align: left;
                background: var(--color-midnight-moss);
                color: var(--color-text-primary);
                border-bottom: 1px solid var(--color-muted-pine);
            }

            .task-table th:last-child {
                width: 60px;
                text-align: center;
            }

            .task-table td {
                padding: 16px 14px 14px 14px;
                border-bottom: 1px solid rgba(91, 122, 114, 0.5);
                color: var(--color-text-primary);
                vertical-align: top;
            }

            .task-table tbody tr {
                margin-bottom: 6px;
            }

            .task-row-wrap > * + * {
                margin-top: 8px;
            }

            .task-text-cell {
                text-align: center;
                vertical-align: middle;
            }

            .task-delete-cell {
                width: 60px;
                text-align: center;
                vertical-align: middle;
            }

            .task-action-stack {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 5px;
            }

            .task-order-row {
                display: flex;
                flex-direction: column;
                gap: 3px;
            }

            .task-row-wrap {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            .task-header {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 12px;
                width: 100%;
            }

            .task-notes {
                margin-top: 8px;
            }

            .task-notes-summary {
                padding: 4px 6px;
                color: var(--color-text-muted);
                cursor: pointer;
                font-size: 13px;
                font-weight: 600;
                list-style-position: inside;
            }

            .task-notes[open] .task-notes-summary {
                margin-bottom: 6px;
            }

            .task-title {
                flex: 1;
                text-align: center;
                font-weight: 700;
                color: var(--color-text-primary);
                font-size: 18px;
                font-weight: 700;
            }

            .task-edit-input,
            .note-edit-input {
                border: 1px solid var(--color-muted-pine);
                border-radius: 6px;
                background: transparent;
                color: inherit;
                box-sizing: border-box;
                outline: none;
            }

            .task-edit-input {
                flex: 1;
                min-width: 0;
                padding: 4px 6px;
                text-align: center;
                font: inherit;
                font-size: 18px;
                font-weight: 700;
            }

            .note-edit-input {
                flex: 1;
                min-width: 0;
                padding: 3px 5px;
                font-size: 14px;
                font-weight: 600;
            }

            .note-input-row {
                display: flex;
                gap: 8px;
                align-items: center;
                width: fit-content;
                max-width: 220px;
                justify-content: flex-start;
            }

            .note-input {
                flex: 0 1 110px;
                width: 110px !important;
                max-width: 100%;
                min-width: 110px;
                padding: 5px 8px !important;
                height: 28px !important;
                border: 1px solid var(--color-muted-pine);
                border-radius: 8px;
                font-size: 13px !important;
                font-weight: 600;
                background: var(--color-deep-forest);
                color: var(--color-text-primary);
                box-sizing: border-box;
            }

            .dash-input.note-input {
                width: 110px !important;
                min-width: 110px;
                max-width: 110px;
            }

            .note-input::placeholder {
                color: var(--color-text-muted);
            }

            .note-button {
                flex: 0 0 auto;
                padding: 7px 10px;
                min-width: 46px;
                border: 1px solid var(--color-muted-pine);
                border-radius: 8px;
                background: linear-gradient(180deg, var(--color-spruce-blue) 0%, var(--color-misty-teal) 100%);
                color: var(--color-dark-slate);
                cursor: pointer;
                font-size: 13px;
                font-weight: 700;
            }

            .order-button {
                width: 24px;
                min-width: 24px;
                height: 24px;
                padding: 0;
                border: 1px solid #4a504e;
                border-radius: 5px;
                background: #3a403e;
                color: #c1c7c4;
                cursor: pointer;
                font-size: 16px;
                font-weight: 700;
                line-height: 1;
            }

            .note-item .order-button + .order-button {
                margin-left: -3px;
            }

            .order-button:hover {
                background: #555d59;
                color: #f0f3f1;
            }

            .notes-list {
                margin: 6px 0 0 0;
                padding: 6px 8px 6px 18px;
                list-style: disc;
                color: var(--color-text-primary);
                font-size: 13px;
                background: rgba(36, 51, 48, 0.7);
                border: none;
                border-radius: 8px;
                line-height: 1.4;
            }

            .note-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 6px;
                margin: 2px 0;
                padding: 2px 0;
                border: none;
                border-radius: 6px;
                background: transparent;
            }

            .note-text {
                flex: 1;
                display: inline-block;
                color: var(--color-text-primary);
                font-size: 14px;
                font-weight: 600;
                line-height: 1.4;
            }

            .completed-note {
                color: var(--color-text-muted);
                font-style: italic;
            }

            .note-edit-wrap {
                position: relative;
                display: flex;
                flex: 1;
                min-width: 0;
            }

            .note-scratch {
                position: absolute;
                top: 50%;
                right: 5px;
                left: 5px;
                height: 10px;
                transform: translateY(-50%) rotate(-2deg);
                background:
                    linear-gradient(174deg, transparent 38%, rgba(222, 188, 151, 0.95) 40%, rgba(222, 188, 151, 0.95) 52%, transparent 54%),
                    linear-gradient(6deg, transparent 42%, rgba(178, 141, 112, 0.9) 44%, rgba(178, 141, 112, 0.9) 56%, transparent 58%);
                pointer-events: none;
                z-index: 2;
            }

            .delete-button {
                width: 28px;
                height: 28px;
                border: 1px solid var(--color-muted-pine);
                border-radius: 8px;
                background: var(--color-ocean-storm);
                color: var(--color-text-primary);
                font-size: 18px;
                font-weight: 700;
                cursor: pointer;
                line-height: 1;
                padding: 0;
            }

            .delete-button:hover {
                background: var(--color-misty-teal);
                color: var(--color-text-primary);
            }

            .empty-state {
                text-align: center;
                color: var(--color-text-muted);
                padding: 18px;
                font-size: 15px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        <script>
            window.addEventListener('load', function () {
                const focusTaskInput = function () {
                    const taskInput = document.getElementById('task-input');
                    if (taskInput) {
                        taskInput.focus();
                        taskInput.select();
                    }
                };

                focusTaskInput();

                document.addEventListener('keydown', function (event) {
                    const active = document.activeElement;
                    if (!active || event.key !== 'Enter') {
                        return;
                    }

                    if (active.id === 'task-input') {
                        event.preventDefault();
                        const addTaskButton = document.querySelector('button[id*="add-button"]');
                        if (addTaskButton) {
                            addTaskButton.click();
                        }
                    }

                    if (active.id && active.id.includes('note-input')) {
                        event.preventDefault();
                        const taskRow = active.closest('.task-row-wrap');
                        const addNoteButton = taskRow ? taskRow.querySelector('button[id*="add-note-button"]') : null;
                        if (addNoteButton) {
                            addNoteButton.click();
                        }
                    }
                });

                document.addEventListener('click', function (event) {
                    const button = event.target.closest('button');
                    if (!button) {
                        return;
                    }

                    const buttonId = button.id || '';

                    if (buttonId.includes('add-button')) {
                        setTimeout(function () {
                            const noteInputs = Array.from(document.querySelectorAll('input[id*="note-input"]'));
                            const lastNoteInput = noteInputs[noteInputs.length - 1];
                            if (lastNoteInput) {
                                lastNoteInput.focus();
                                lastNoteInput.select();
                            }
                        }, 80);
                    }

                    if (buttonId.includes('add-note-button')) {
                        setTimeout(function () {
                            const taskRow = button.closest('.task-row-wrap');
                            const noteInput = taskRow ? taskRow.querySelector('input[id*="note-input"]') : null;
                            if (noteInput) {
                                noteInput.focus();
                                noteInput.select();
                            }
                        }, 80);
                    }
                });

                const taskNotesStateKey = 'todo-task-notes-open';
                const restoreTaskNotesState = function () {
                    let savedState = {};
                    try {
                        savedState = JSON.parse(localStorage.getItem(taskNotesStateKey) || '{}');
                    } catch (error) {
                        savedState = {};
                    }

                    document.querySelectorAll('details.task-notes').forEach(function (details) {
                        const taskId = details.dataset.taskId;
                        if (taskId && Object.prototype.hasOwnProperty.call(savedState, taskId)) {
                            details.open = savedState[taskId];
                        }
                        if (details.dataset.stateBound === 'true') {
                            return;
                        }
                        details.dataset.stateBound = 'true';
                        details.addEventListener('toggle', function () {
                            savedState[taskId] = details.open;
                            localStorage.setItem(taskNotesStateKey, JSON.stringify(savedState));
                        });
                    });
                };

                restoreTaskNotesState();
                new MutationObserver(restoreTaskNotesState).observe(document.body, {
                    childList: true,
                    subtree: true
                });
            });
        </script>
    </body>
</html>
'''

WARM_NEUTRAL_PALETTES = [
    {
        'surface': '#2e3b34',
        'notes': '#3b4b42',
        'border': '#799581',
        'button': '#9dbb9b',
        'button_text': '#17231d',
        'input': '#202b27',
        'text': '#eef4ef',
        'muted': '#b9cbbd'
    },
    {
        'surface': '#293743',
        'notes': '#344753',
        'border': '#7896a5',
        'button': '#9bb8c5',
        'button_text': '#17232a',
        'input': '#1e2931',
        'text': '#e9f1f4',
        'muted': '#b6c8d0'
    },
    {
        'surface': '#49352d',
        'notes': '#5a4237',
        'border': '#c38b6b',
        'button': '#d8a27d',
        'button_text': '#241811',
        'input': '#2d211d',
        'text': '#f7e9dc',
        'muted': '#d8bda8'
    },
    {
        'surface': '#403243',
        'notes': '#504054',
        'border': '#aa8dab',
        'button': '#c8a5c4',
        'button_text': '#241827',
        'input': '#2c222f',
        'text': '#f3e9f2',
        'muted': '#d3bdd2'
    },
    {
        'surface': '#443c28',
        'notes': '#574c31',
        'border': '#b6a064',
        'button': '#d0b86f',
        'button_text': '#292311',
        'input': '#2d281c',
        'text': '#f4efdc',
        'muted': '#d5c99d'
    }
]

THEME_ORDER = list(range(len(WARM_NEUTRAL_PALETTES)))
random.shuffle(THEME_ORDER)


def get_palette(index=None):
    if index is None:
        index = random.randint(0, len(WARM_NEUTRAL_PALETTES) - 1)
    return WARM_NEUTRAL_PALETTES[index % len(WARM_NEUTRAL_PALETTES)]


def random_palette():
    return get_palette()


def fetch_tasks_df():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                WITH ordered_tasks AS (
                    SELECT task_id, ROW_NUMBER() OVER (ORDER BY sort_order, task_id) AS new_order
                    FROM tasks
                )
                UPDATE tasks
                SET sort_order = ordered_tasks.new_order
                FROM ordered_tasks
                WHERE tasks.task_id = ordered_tasks.task_id
            ''')
            cur.execute('''
                WITH ordered_notes AS (
                    SELECT note_id,
                           ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY sort_order, note_id) AS new_order
                    FROM notes
                )
                UPDATE notes
                SET sort_order = ordered_notes.new_order
                FROM ordered_notes
                WHERE notes.note_id = ordered_notes.note_id
            ''')
            conn.commit()
            cur.execute('SELECT task_id, task_value FROM tasks ORDER BY sort_order, task_id')
            task_rows = cur.fetchall()

            if not task_rows:
                return pd.DataFrame({'ID': [], 'Task': [], 'Notes': [], 'Theme': []})

            task_ids = [task_id for task_id, _ in task_rows]
            placeholders = ', '.join(['%s'] * len(task_ids))
            cur.execute(
                f"SELECT task_id, note_value, completed FROM notes WHERE task_id IN ({placeholders}) ORDER BY sort_order, note_id",
                task_ids,
            )
            notes_by_task = {}
            for task_id, note_value, completed in cur.fetchall():
                notes_by_task.setdefault(task_id, []).append({
                    'text': note_value,
                    'completed': completed,
                })

            rows = []
            for task_id, task_value in task_rows:
                rows.append({
                    'ID': task_id,
                    'Task': task_value,
                    'Notes': notes_by_task.get(task_id, []),
                    'Theme': THEME_ORDER[task_id % len(THEME_ORDER)]
                })

    return pd.DataFrame(rows, columns=['ID', 'Task', 'Notes', 'Theme'])


initial_data = fetch_tasks_df()

# Store for managing data
app.layout = html.Div([
    dcc.Store(id='todo-store', data=initial_data.to_json(date_format='iso', orient='split')),

    html.Div([
        html.H1("Tasks", style={'textAlign': 'center', 'marginBottom': '26px', 'color': '#e4ebe7'}),

        html.Div([
            dcc.Input(
                id='task-input',
                type='text',
                placeholder='Enter a new task...',
                className='task-input',
                autoFocus=True
            ),
            html.Button(
                'Add Task',
                id='add-button',
                n_clicks=0,
                className='add-button'
            )
        ], className='todo-input-row'),

        html.Div(id='task-table', className='task-table-wrap'),

        html.Details([
            html.Summary('PostgreSQL Query Executor', className='query-summary'),
            dcc.Textarea(
                id='query-input',
                className='query-input',
                value='/* TASKS and NOTES tables */',
                spellCheck=False,
                style={
                    'backgroundColor': '#1a2421',
                    'color': '#e4ebe7',
                    'borderColor': '#3b5249'
                }
            ),
            html.Div([
                html.Button('Run Query', id='query-run-button', n_clicks=0, className='query-button'),
                html.Span(id='query-status', className='query-status')
            ], className='query-actions'),
            html.Div([
                html.Div('Results', className='query-results-label'),
                html.Div(id='query-results', className='query-results')
            ])
        ], className='query-panel', open=False)
    ], className='todo-app')
])

def correct_spelling(text):
    if not text:
        return ''

    if SpellChecker is None:
        return text

    checker = SpellChecker(distance=1)
    corrected_words = []
    for word in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text):
        corrected = checker.correction(word) or word
        corrected_words.append(corrected)

    corrected_text = text
    for original, corrected in zip(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text), corrected_words):
        corrected_text = corrected_text.replace(original, corrected, 1)

    return corrected_text


def format_task_value(task_value):
    if task_value:
        corrected = correct_spelling(task_value.strip())
        return corrected.title()
    return ''


def format_note_value(note_value):
    if not note_value:
        return ''

    text = correct_spelling(' '.join(str(note_value).strip().split()))
    if not text:
        return ''

    sentences = [part.strip() for part in text.split('. ') if part.strip()]
    if not sentences:
        return text[0].upper() + text[1:].lower()

    formatted = []
    for index, sentence in enumerate(sentences):
        if not sentence:
            continue
        sentence = sentence[0].upper() + sentence[1:].lower()
        formatted.append(sentence)

    return '. '.join(formatted) + ('.' if text.endswith('.') else '')


def normalize_notes(notes):
    if notes is None:
        return []
    if isinstance(notes, str):
        notes = [notes]
    if isinstance(notes, tuple):
        notes = list(notes)
    if not isinstance(notes, list):
        return []
    cleaned = []
    for note in notes:
        if note is None:
            continue
        completed = False
        if isinstance(note, dict):
            completed = bool(note.get('completed', False))
            note = note.get('text', note.get('value', ''))
        text = format_note_value(note)
        if text:
            cleaned.append({'text': text, 'completed': completed})
    return cleaned


def load_store(current_store):
    if not current_store:
        return pd.DataFrame({'ID': [], 'Task': [], 'Notes': [], 'Theme': []})
    try:
        df = pd.read_json(StringIO(current_store), orient='split')
    except ValueError:
        return pd.DataFrame({'ID': [], 'Task': [], 'Notes': [], 'Theme': []})

    if 'Notes' in df.columns:
        df['Notes'] = df['Notes'].apply(normalize_notes)
    if 'Theme' not in df.columns:
        df['Theme'] = [random.randint(0, len(WARM_NEUTRAL_PALETTES) - 1) for _ in range(len(df))]
    else:
        df['Theme'] = df['Theme'].apply(lambda theme: theme if isinstance(theme, (int, float)) else 0)
    return df


def note_value_outputs(note_values):
    if note_values is None:
        return []
    if not isinstance(note_values, list):
        return [str(note_values)]
    return list(note_values)


@callback(
    Output('todo-store', 'data'),
    Output('task-input', 'value'),
    Output({'type': 'note-input', 'index': ALL}, 'value'),
    Input('add-button', 'n_clicks'),
    Input({'type': 'delete-button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'add-note-button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'note-complete-button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'note-delete-button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'save-task-button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'save-note-button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'task-move-up', 'index': ALL}, 'n_clicks'),
    Input({'type': 'task-move-down', 'index': ALL}, 'n_clicks'),
    Input({'type': 'note-move-up', 'index': ALL}, 'n_clicks'),
    Input({'type': 'note-move-down', 'index': ALL}, 'n_clicks'),
    State('task-input', 'value'),
    State({'type': 'note-input', 'index': ALL}, 'value'),
    State({'type': 'task-edit', 'index': ALL}, 'value'),
    State({'type': 'note-edit', 'index': ALL}, 'value'),
    State('todo-store', 'data'),
    prevent_initial_call=True
)
def update_tasks(add_clicks, delete_clicks, add_note_clicks, note_complete_clicks, note_delete_clicks,
                 save_task_clicks, save_note_clicks, task_move_up_clicks, task_move_down_clicks,
                 note_move_up_clicks, note_move_down_clicks, task_value, note_values,
                 task_edit_values, note_edit_values, current_store):
    trigger = ctx.triggered_id
    note_values = note_values or []
    task_edit_values = task_edit_values or []
    note_edit_values = note_edit_values or []

    if trigger == 'add-button':
        formatted_task = format_task_value(task_value)
        if not formatted_task:
            return current_store, '', note_value_outputs(note_values)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tasks (user_id, task_value, sort_order) "
                    "VALUES (%s, %s, COALESCE((SELECT MAX(sort_order) + 1 FROM tasks), 1))",
                    ('local', formatted_task),
                )
            conn.commit()

        refreshed = fetch_tasks_df()
        return refreshed.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

    if isinstance(trigger, dict):
        trigger_type = trigger.get('type')
        trigger_index = trigger.get('index')

        if trigger_type == 'delete-button':
            if trigger_index is None:
                return current_store, '', note_value_outputs(note_values)

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM tasks WHERE task_id = %s', (trigger_index,))
                conn.commit()

            refreshed = fetch_tasks_df()
            return refreshed.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

        if trigger_type == 'save-task-button':
            task_df = fetch_tasks_df()
            task_ids = task_df['ID'].tolist()
            if trigger_index not in task_ids:
                return current_store, '', note_value_outputs(note_values)
            task_position = task_ids.index(trigger_index)
            edited_task = task_edit_values[task_position] if len(task_edit_values) > task_position else ''
            formatted_task = format_task_value(edited_task)
            if not formatted_task:
                return current_store, '', note_value_outputs(note_values)

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'UPDATE tasks SET task_value = %s WHERE task_id = %s',
                        (formatted_task, trigger_index),
                    )
                conn.commit()

            refreshed = fetch_tasks_df()
            return refreshed.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

        if trigger_type == 'save-note-button':
            if not trigger_index:
                return current_store, '', note_value_outputs(note_values)
            parts = str(trigger_index).split('-')
            if len(parts) != 2:
                return current_store, '', note_value_outputs(note_values)
            task_id = int(parts[0])
            note_index = int(parts[1])

            task_df = fetch_tasks_df()
            task_ids = task_df['ID'].tolist()
            if task_id not in task_ids:
                return current_store, '', note_value_outputs(note_values)
            note_position = sum(len(normalize_notes(notes)) for notes in task_df.iloc[:task_ids.index(task_id)]['Notes']) + note_index
            edited_note = note_edit_values[note_position] if len(note_edit_values) > note_position else ''
            formatted_note = format_note_value(edited_note)
            if not formatted_note:
                return current_store, '', note_value_outputs(note_values)

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT note_id FROM notes WHERE task_id = %s ORDER BY sort_order, note_id',
                        (task_id,),
                    )
                    note_rows = cur.fetchall()
                    if note_index < 0 or note_index >= len(note_rows):
                        return current_store, '', note_value_outputs(note_values)
                    cur.execute(
                        'UPDATE notes SET note_value = %s WHERE note_id = %s',
                        (formatted_note, note_rows[note_index][0]),
                    )
                conn.commit()

            refreshed = fetch_tasks_df()
            return refreshed.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

        if trigger_type in ('task-move-up', 'task-move-down'):
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT task_id, sort_order FROM tasks ORDER BY sort_order, task_id')
                    task_rows = cur.fetchall()
                    task_ids = [task_id for task_id, _ in task_rows]
                    if trigger_index not in task_ids:
                        return current_store, '', note_value_outputs(note_values)
                    current_position = task_ids.index(trigger_index)
                    neighbor_position = current_position - 1 if trigger_type == 'task-move-up' else current_position + 1
                    if neighbor_position < 0 or neighbor_position >= len(task_rows):
                        return current_store, '', note_value_outputs(note_values)
                    current_id, current_order = task_rows[current_position]
                    neighbor_id, neighbor_order = task_rows[neighbor_position]
                    cur.execute('UPDATE tasks SET sort_order = %s WHERE task_id = %s', (neighbor_order, current_id))
                    cur.execute('UPDATE tasks SET sort_order = %s WHERE task_id = %s', (current_order, neighbor_id))
                conn.commit()

            refreshed = fetch_tasks_df()
            return refreshed.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

        if trigger_type in ('note-move-up', 'note-move-down'):
            parts = str(trigger_index).split('-')
            if len(parts) != 2:
                return current_store, '', note_value_outputs(note_values)
            task_id = int(parts[0])
            note_index = int(parts[1])
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT note_id, sort_order FROM notes WHERE task_id = %s ORDER BY sort_order, note_id',
                        (task_id,),
                    )
                    note_rows = cur.fetchall()
                    neighbor_position = note_index - 1 if trigger_type == 'note-move-up' else note_index + 1
                    if note_index < 0 or note_index >= len(note_rows) or neighbor_position < 0 or neighbor_position >= len(note_rows):
                        return current_store, '', note_value_outputs(note_values)
                    current_id, current_order = note_rows[note_index]
                    neighbor_id, neighbor_order = note_rows[neighbor_position]
                    cur.execute('UPDATE notes SET sort_order = %s WHERE note_id = %s', (neighbor_order, current_id))
                    cur.execute('UPDATE notes SET sort_order = %s WHERE note_id = %s', (current_order, neighbor_id))
                conn.commit()

            refreshed = fetch_tasks_df()
            return refreshed.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

        if trigger_type in ('note-complete-button', 'note-delete-button'):
            if not trigger_index:
                return current_store, '', note_value_outputs(note_values)

            if isinstance(trigger_index, str):
                parts = trigger_index.split('-')
                if len(parts) != 2:
                    return current_store, '', note_value_outputs(note_values)
                task_id = int(parts[0])
                note_index = int(parts[1])
            else:
                task_id, note_index = trigger_index

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT note_id FROM notes WHERE task_id = %s ORDER BY sort_order, note_id',
                        (task_id,),
                    )
                    note_rows = cur.fetchall()
                    if note_index < 0 or note_index >= len(note_rows):
                        return current_store, '', note_value_outputs(note_values)
                    note_id = note_rows[note_index][0]
                    if trigger_type == 'note-complete-button':
                        cur.execute(
                            'UPDATE notes SET completed = NOT completed WHERE note_id = %s',
                            (note_id,),
                        )
                    else:
                        cur.execute('DELETE FROM notes WHERE note_id = %s', (note_id,))
                conn.commit()

            refreshed = fetch_tasks_df()
            return refreshed.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

        if trigger_type == 'add-note-button':
            task_id = trigger_index
            task_df = fetch_tasks_df()
            task_ids = task_df['ID'].tolist()
            if task_id not in task_ids:
                return current_store, '', note_value_outputs(note_values)

            task_position = task_ids.index(task_id)
            note_value = note_values[task_position] if note_values and len(note_values) > task_position else ''
            if not note_value or not note_value.strip():
                return current_store, '', note_value_outputs(note_values)

            formatted_note = format_note_value(note_value)
            if not formatted_note:
                return current_store, '', note_value_outputs(note_values)

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO notes (task_id, note_value, sort_order) '
                        'VALUES (%s, %s, COALESCE((SELECT MAX(sort_order) + 1 FROM notes WHERE task_id = %s), 1))',
                        (task_id, formatted_note, task_id),
                    )
                conn.commit()

            cleared_values = list(note_values)
            if len(cleared_values) > task_position:
                cleared_values[task_position] = ''
            refreshed = fetch_tasks_df()
            return refreshed.to_json(date_format='iso', orient='split'), '', cleared_values

    return current_store, '', note_value_outputs(note_values)

@callback(
    Output('task-table', 'children'),
    Input('todo-store', 'data')
)
def update_table(data):
    df = load_store(data)

    if df.empty:
        return html.P("No tasks yet.", className='empty-state')

    rows = []
    for _, row in df.iterrows():
        notes = normalize_notes(row.get('Notes', []))
        theme_index = int(row.get('Theme', 0) or 0)
        theme = get_palette(theme_index)
        note_items = []
        for i, note in enumerate(notes):
            note_text = note['text']
            note_completed = note['completed']
            note_items.append(
                html.Li([
                    html.Div([
                        dcc.Input(
                            value=note_text,
                            type='text',
                            className=f"note-edit-input{' completed-note' if note_completed else ''}",
                            id={'type': 'note-edit', 'index': f"{row['ID']}-{i}"},
                            style={'background': theme['input'],
                                   'color': '#756b61' if note_completed else theme['text'],
                                   'borderColor': theme['border'],
                                   'textAlign': 'center',
                                   'backgroundImage': (
                                       'repeating-linear-gradient(-4deg, '
                                       'transparent 0, transparent 3px, '
                                       'rgba(25, 22, 19, 0.86) 3px, '
                                       'rgba(25, 22, 19, 0.86) 4px, '
                                       'transparent 4px, transparent 7px), '
                                       'repeating-linear-gradient(3deg, '
                                       'transparent 0, transparent 5px, '
                                       'rgba(55, 45, 38, 0.7) 5px, '
                                       'rgba(55, 45, 38, 0.7) 6px, '
                                       'transparent 6px, transparent 9px)'
                                   ) if note_completed else 'none',
                                   'backgroundRepeat': 'no-repeat',
                                   'backgroundPosition': 'center',
                                   'backgroundSize': '100% 18px'}
                        ),
                    ], className='note-edit-wrap'),
                    html.Button(
                        'Save',
                        n_clicks=0,
                        className='note-complete-button',
                        title='Save note changes',
                        id={'type': 'save-note-button', 'index': f"{row['ID']}-{i}"},
                        style={'padding': '3px 7px', 'fontSize': '12px', 'fontWeight': '700', 'minWidth': '42px',
                               'background': theme['button'], 'color': theme['button_text'],
                               'borderColor': theme['border']}
                    ),
                    html.Button(
                        'Undo' if note_completed else 'Done',
                        n_clicks=0,
                        className='note-complete-button',
                        title='Mark note incomplete' if note_completed else 'Cross off note',
                        id={'type': 'note-complete-button', 'index': f"{row['ID']}-{i}"},
                        style={'padding': '3px 7px', 'fontSize': '12px', 'fontWeight': '700', 'minWidth': '42px',
                               'background': theme['button'], 'color': theme['button_text'],
                               'borderColor': theme['border']}
                    ),
                    html.Button(
                        '↑',
                        n_clicks=0,
                        className='order-button',
                        title='Move note up',
                        id={'type': 'note-move-up', 'index': f"{row['ID']}-{i}"},
                        style={'background': theme['button'], 'color': theme['button_text'], 'borderColor': theme['border']}
                    ),
                    html.Button(
                        '↓',
                        n_clicks=0,
                        className='order-button',
                        title='Move note down',
                        id={'type': 'note-move-down', 'index': f"{row['ID']}-{i}"},
                        style={'background': theme['button'], 'color': theme['button_text'], 'borderColor': theme['border']}
                    ),
                    html.Button(
                        '×',
                        n_clicks=0,
                        className='delete-button',
                        title='Delete note permanently',
                        id={'type': 'note-delete-button', 'index': f"{row['ID']}-{i}"},
                        style={'width': '22px', 'height': '22px', 'fontSize': '14px', 'fontWeight': '700', 'minWidth': '22px',
                               'background': theme['button'], 'color': theme['button_text'],
                               'borderColor': theme['border']}
                    )
                ], className='note-item')
            )

        task_style = {
            'background': theme['surface'],
            'border': f"1px solid {theme['border']}",
            'borderRadius': '14px',
            'boxShadow': f"0 8px 18px {theme['border']}33",
            'padding': '12px 14px'
        }

        notes_style = {
            'background': theme['notes'],
            'border': f"1px solid {theme['border']}",
            'color': theme['text']
        }

        input_style = {
            'background': theme['input'],
            'color': theme['text'],
            'borderColor': theme['border'],
            'width': '140px',
            'maxWidth': '100%',
            'boxSizing': 'border-box'
        }

        rows.append(
            html.Tr([
                html.Td([
                    html.Div(
                        [
                            html.Div([
                                dcc.Input(
                                    value=row['Task'],
                                    type='text',
                                    className='task-edit-input',
                                    id={'type': 'task-edit', 'index': row['ID']},
                                     style={'background': theme['input'], 'color': theme['text'],
                                         'borderColor': theme['border']}
                                ),
                                html.Button(
                                    'Save',
                                    n_clicks=0,
                                    className='note-complete-button',
                                    title='Save task changes',
                                    id={'type': 'save-task-button', 'index': row['ID']},
                                    style={'padding': '5px 8px', 'fontSize': '12px', 'fontWeight': '700', 'minWidth': '46px',
                                           'background': theme['button'], 'color': theme['button_text'],
                                           'borderColor': theme['border']}
                                ),
                            ], className='task-header'),
                            html.Details([
                                html.Summary(
                                    f"Notes ({len(notes)})",
                                    className='task-notes-summary'
                                ),
                                html.Ul(note_items, className='notes-list', style=notes_style) if note_items else None,
                                html.Div([
                                    dcc.Input(
                                        id={'type': 'note-input', 'index': row['ID']},
                                        type='text',
                                        placeholder='add note',
                                        className='note-input',
                                        style={
                                            **input_style,
                                            'width': '110px',
                                            'minWidth': '110px',
                                            'maxWidth': '110px',
                                            'padding': '5px 8px',
                                            'height': '28px',
                                            'fontSize': '13px',
                                            'fontWeight': '600'
                                        }
                                    ),
                                    html.Button(
                                        'Add',
                                        id={'type': 'add-note-button', 'index': row['ID']},
                                        n_clicks=0,
                                        className='note-button',
                                        style={'background': theme['button'], 'color': theme['button_text'], 'borderColor': theme['border'], 'padding': '7px 10px', 'minWidth': '46px'}
                                    )
                                ], className='note-input-row')
                                     ], className='task-notes', open=False,
                                         **{'data-task-id': str(row['ID'])})
                        ],
                        className='task-row-wrap',
                        style=task_style
                    )
                ], className='task-text-cell', style={'padding': '10px', 'borderBottom': '1px solid #ddd'}),
                html.Td(
                    html.Div([
                        html.Button(
                            '×',
                            n_clicks=0,
                            className='delete-button',
                            id={'type': 'delete-button', 'index': row['ID']},
                            style={'background': theme['button'], 'color': theme['button_text'], 'borderColor': theme['border']}
                        ),
                        html.Div([
                            html.Button(
                                '↑',
                                n_clicks=0,
                                className='order-button',
                                title='Move task up',
                                id={'type': 'task-move-up', 'index': row['ID']},
                                style={'background': theme['button'], 'color': theme['button_text'], 'borderColor': theme['border']}
                            ),
                            html.Button(
                                '↓',
                                n_clicks=0,
                                className='order-button',
                                title='Move task down',
                                id={'type': 'task-move-down', 'index': row['ID']},
                                style={'background': theme['button'], 'color': theme['button_text'], 'borderColor': theme['border']}
                            )
                        ], className='task-order-row')
                    ], className='task-action-stack'),
                    className='task-delete-cell',
                    style={'padding': '10px', 'borderBottom': '1px solid #ddd'}
                )
            ])
        )

    return html.Table([
        html.Tbody(rows)
    ], className='task-table')


@callback(
    Output('query-results', 'children'),
    Output('query-status', 'children'),
    Input('query-run-button', 'n_clicks'),
    State('query-input', 'value'),
    prevent_initial_call=True
)
def run_query(n_clicks, query_text):
    query = (query_text or '').strip()
    query_for_validation = query
    while query_for_validation.startswith('/*'):
        comment_end = query_for_validation.find('*/', 2)
        if comment_end == -1:
            return '', 'Close the SQL block comment before running the query.'
        query_for_validation = query_for_validation[comment_end + 2:].lstrip()

    if not query_for_validation:
        return '', 'Enter a SELECT query first.'

    if not re.match(r'^SELECT\b', query_for_validation, flags=re.IGNORECASE):
        return '', 'Only read-only SELECT queries are allowed.'

    query_without_final_semicolon = query_for_validation.rstrip(';').rstrip()
    if ';' in query_without_final_semicolon:
        return '', 'Run one query at a time; multiple statements are not allowed.'

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SET TRANSACTION READ ONLY')
                cur.execute(query)
                columns = [column.name for column in cur.description or []]
                result_rows = cur.fetchmany(500)
                has_more_rows = cur.fetchone() is not None

        if not columns:
            return html.P('Query completed without a result set.'), 'Query completed.'

        header = html.Tr([html.Th(column) for column in columns])
        body = [
            html.Tr([
                html.Td('NULL' if value is None else str(value))
                for value in row
            ])
            for row in result_rows
        ]
        result_table = html.Table(
            [html.Thead(header), html.Tbody(body)],
            className='query-result-table'
        )
        row_status = f'{len(result_rows)} row(s) returned'
        if has_more_rows:
            row_status += ' (showing the first 500)'
        return result_table, row_status
    except psycopg.Error as error:
        return '', f'Query error: {error}'.split('\n')[0]
    except Exception as error:
        return '', f'Query error: {error}'

if __name__ == '__main__':
    app.run(debug=True)
