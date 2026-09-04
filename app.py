import re

import dash
from dash import ALL, dcc, html, Input, Output, State, callback
from dash import callback_context as ctx
import pandas as pd
from datetime import datetime
from io import StringIO

try:
    from spellchecker import SpellChecker
except ImportError:
    SpellChecker = None

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
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(180deg, var(--color-dark-slate) 0%, var(--color-deep-forest) 100%);
                color: var(--color-text-primary);
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
                padding: 12px 14px;
                font-size: clamp(14px, 1.2vw, 16px);
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
                padding: 12px 16px;
                border: 1px solid var(--color-muted-pine);
                border-radius: 12px;
                background: linear-gradient(180deg, var(--color-ocean-storm) 0%, var(--color-muted-pine) 100%);
                color: var(--color-text-primary);
                font-weight: 600;
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

            .task-title {
                flex: 1;
                text-align: center;
                font-weight: 600;
                color: var(--color-text-primary);
            }

            .note-input-row {
                display: flex;
                gap: 8px;
                align-items: center;
            }

            .note-input {
                flex: 1;
                padding: 7px 10px;
                border: 1px solid var(--color-muted-pine);
                border-radius: 8px;
                font-size: 12px;
                background: var(--color-deep-forest);
                color: var(--color-text-primary);
            }

            .note-input::placeholder {
                color: var(--color-text-muted);
            }

            .note-button {
                padding: 7px 10px;
                border: 1px solid var(--color-muted-pine);
                border-radius: 8px;
                background: linear-gradient(180deg, var(--color-spruce-blue) 0%, var(--color-misty-teal) 100%);
                color: var(--color-dark-slate);
                cursor: pointer;
                font-size: 12px;
                font-weight: 600;
            }

            .notes-list {
                margin: 6px 0 0 0;
                padding: 6px 8px 6px 18px;
                list-style: disc;
                color: var(--color-text-primary);
                font-size: 11px;
                background: rgba(36, 51, 48, 0.7);
                border: 1px solid rgba(91, 122, 114, 0.5);
                border-radius: 8px;
                line-height: 1.35;
            }

            .note-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 6px;
                margin: 2px 0;
                padding: 2px 0;
            }

            .note-text {
                flex: 1;
                display: inline-block;
                color: var(--color-text-primary);
                font-size: 11px;
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
            });
        </script>
    </body>
</html>
'''

# Create initial DataFrame for to-do list
initial_data = pd.DataFrame({
    'ID': [],
    'Task': [],
    'Notes': []
})

# Store for managing data
app.layout = html.Div([
    dcc.Store(id='todo-store', data=initial_data.to_json(date_format='iso', orient='split')),

    html.Div([
        html.H1("To-Do List", style={'textAlign': 'center', 'marginBottom': '26px', 'color': '#e4ebe7'}),

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
        text = format_note_value(note)
        if text:
            cleaned.append(text)
    return cleaned


def load_store(current_store):
    if not current_store:
        return pd.DataFrame({'ID': [], 'Task': [], 'Notes': []})
    try:
        df = pd.read_json(StringIO(current_store), orient='split')
    except ValueError:
        return pd.DataFrame({'ID': [], 'Task': [], 'Notes': []})

    if 'Notes' in df.columns:
        df['Notes'] = df['Notes'].apply(normalize_notes)
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
    Input({'type': 'note-delete-button', 'index': ALL}, 'n_clicks'),
    State('task-input', 'value'),
    State({'type': 'note-input', 'index': ALL}, 'value'),
    State('todo-store', 'data'),
    prevent_initial_call=True
)
def update_tasks(add_clicks, delete_clicks, add_note_clicks, note_delete_clicks, task_value, note_values, current_store):
    trigger = ctx.triggered_id
    df = load_store(current_store)

    note_values = note_values or []

    if trigger == 'add-button':
        formatted_task = format_task_value(task_value)
        if not formatted_task:
            return current_store, '', note_value_outputs(note_values)

        new_id = len(df) + 1
        new_row = {'ID': new_id, 'Task': formatted_task, 'Notes': []}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        return df.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

    if isinstance(trigger, dict):
        trigger_type = trigger.get('type')
        trigger_index = trigger.get('index')

        if trigger_type == 'delete-button':
            if df.empty:
                return current_store, '', note_value_outputs(note_values)
            df = df[df['ID'] != trigger_index].reset_index(drop=True)
            if df.empty:
                return pd.DataFrame({'ID': [], 'Task': [], 'Notes': []}).to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)
            return df.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

        if trigger_type == 'note-delete-button':
            if df.empty or not trigger_index:
                return current_store, '', note_value_outputs(note_values)
            if isinstance(trigger_index, str):
                parts = trigger_index.split('-')
                if len(parts) != 2:
                    return current_store, '', note_value_outputs(note_values)
                task_id = int(parts[0])
                note_index = int(parts[1])
            else:
                task_id, note_index = trigger_index
            task_mask = df['ID'] == task_id
            if not task_mask.any():
                return current_store, '', note_value_outputs(note_values)
            note_list = normalize_notes(df.loc[task_mask, 'Notes'].iloc[0])
            note_list = [n for i, n in enumerate(note_list) if i != note_index]
            target_index = df.index[task_mask].tolist()[0]
            df.at[target_index, 'Notes'] = note_list
            return df.to_json(date_format='iso', orient='split'), '', note_value_outputs(note_values)

        if trigger_type == 'add-note-button':
            if df.empty:
                return current_store, '', note_value_outputs(note_values)
            task_id = trigger_index
            task_ids = df['ID'].tolist()
            if task_id not in task_ids:
                return current_store, '', note_value_outputs(note_values)
            task_position = task_ids.index(task_id)
            note_value = note_values[task_position] if note_values and len(note_values) > task_position else ''
            if not note_value or not note_value.strip():
                return current_store, '', note_value_outputs(note_values)

            target_index = df.index[df['ID'] == task_id][0]
            note_list = normalize_notes(df.at[target_index, 'Notes'])
            note_list.append(format_note_value(note_value))
            df.at[target_index, 'Notes'] = note_list

            cleared_values = list(note_values)
            if len(cleared_values) > task_position:
                cleared_values[task_position] = ''
            return df.to_json(date_format='iso', orient='split'), '', cleared_values

    return current_store, '', note_value_outputs(note_values)

@callback(
    Output('task-table', 'children'),
    Input('todo-store', 'data')
)
def update_table(data):
    df = load_store(data)

    if df.empty:
        return html.P("No tasks yet. Add one to get started!", className='empty-state')

    rows = []
    for _, row in df.iterrows():
        notes = normalize_notes(row.get('Notes', []))
        note_items = []
        for i, note in enumerate(notes):
            note_items.append(
                html.Li([
                    html.Span(note, className='note-text'),
                    html.Button(
                        '×',
                        n_clicks=0,
                        className='delete-button',
                        id={'type': 'note-delete-button', 'index': f"{row['ID']}-{i}"},
                        style={'width': '18px', 'height': '18px', 'fontSize': '12px', 'minWidth': '18px'}
                    )
                ], className='note-item')
            )

        rows.append(
            html.Tr([
                html.Td([
                    html.Div(
                        [
                            html.Div([
                                html.Div(row['Task'], className='task-title'),
                            ], className='task-header'),
                            html.Ul(note_items, className='notes-list') if note_items else None,
                            html.Div([
                                dcc.Input(
                                    id={'type': 'note-input', 'index': row['ID']},
                                    type='text',
                                    placeholder='add note',
                                    className='note-input'
                                ),
                                html.Button(
                                    'Add',
                                    id={'type': 'add-note-button', 'index': row['ID']},
                                    n_clicks=0,
                                    className='note-button'
                                )
                            ], className='note-input-row')
                        ],
                        className='task-row-wrap'
                    )
                ], className='task-text-cell', style={'padding': '10px', 'borderBottom': '1px solid #ddd'}),
                html.Td(
                    html.Button(
                        '×',
                        n_clicks=0,
                        className='delete-button',
                        id={'type': 'delete-button', 'index': row['ID']}
                    ),
                    className='task-delete-cell',
                    style={'padding': '10px', 'borderBottom': '1px solid #ddd'}
                )
            ])
        )

    return html.Table([
        html.Tbody(rows)
    ], className='task-table')

if __name__ == '__main__':
    app.run(debug=True)
