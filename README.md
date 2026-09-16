# ToDo

To-Do app with local PostgreSQL connectivity.

## Prerequisites

- Python 3.13+
- PostgreSQL installed locally
- A database named `todo_app`
- A PostgreSQL user named `todo_app_user` with `todo_password`

## Quick start

After the one-time setup below, use these commands each time you start the app:

```powershell
cd C:\Users\evanf\Code\ToDo
.\.venv\Scripts\Activate.ps1
python app.py
```

Or launch directly without activating the environment:

```powershell
cd C:\Users\evanf\Code\ToDo
& .\.venv\Scripts\python.exe app.py
```

The app connects to local PostgreSQL with these development credentials:

```text
Host:     localhost
Port:     5432
Database: todo_app
User:     todo_app_user
Password: todo_password
```

If PostgreSQL reports a password authentication failure, reset the local user's password as the PostgreSQL administrator. 
Open **PowerShell as Administrator** for the service commands below. 
The `psql` commands can be run there while
`pg_hba.conf` temporarily allows `trust` authentication.

The PostgreSQL 18 configuration file is usually:

```text
C:\Program Files\PostgreSQL\18\data\pg_hba.conf
```

Temporarily change the local IPv4 and IPv6 `host` entries to `trust`, then run:

```powershell
Restart-Service -Name postgresql-x64-18
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -h localhost -d postgres -c "CREATE ROLE todo_app_user LOGIN PASSWORD 'todo_password';"
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -h localhost -d postgres -c "CREATE DATABASE todo_app OWNER todo_app_user;"
```

If either object already exists, use these commands instead:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -h localhost -d postgres -c "ALTER ROLE todo_app_user WITH PASSWORD 'todo_password';"
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -h localhost -d todo_app -c "GRANT USAGE, CREATE ON SCHEMA public TO todo_app_user;"
```

After the database and role are ready, change those `trust` entries back to
`scram-sha-256`, restart PostgreSQL, and start the app:

```powershell
Restart-Service -Name postgresql-x64-18
cd C:\Users\evanf\Code\ToDo
.\.venv\Scripts\Activate.ps1
python app.py
```

## Upcoming Changes

Planned work for hosting the application on an Ubuntu server:

- Move PostgreSQL to the Ubuntu server and migrate the local database.
- Store database credentials in environment variables instead of `app.py`.
- Install the Python dependencies in a server-side virtual environment.
- Run the Dash app with a production WSGI server such as Gunicorn.
- Add a `systemd` service so the application starts automatically.
- Put Nginx in front of the app for a stable public URL and HTTPS.
- Restrict PostgreSQL access so it is not exposed publicly.

## Local setup

From the project folder:

```powershell
cd C:\Users\evanf\Code\ToDo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install dash pandas psycopg[binary]
```

## Run the app

```powershell
cd C:\Users\evanf\Code\ToDo
.\.venv\Scripts\Activate.ps1
python app.py
```

The Dash app will start locally and connect to PostgreSQL using:

- host: `localhost`
- port: `5432`
- database: `todo_app`
- user: `todo_app_user`
- password: `todo_password`

## Optional direct run without activating

```powershell
cd C:\Users\evanf\Code\ToDo
& .\.venv\Scripts\python.exe app.py
```

## PostgreSQL schema

```sql
CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'local',
    task_value TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE notes (
    note_id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    note_value TEXT NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0
);
```

Existing databases are upgraded automatically when the app starts. Use the
dark-gray up/down arrows to change task priority or reorder notes within a task.
Priority values are normalized to `1, 2, 3, ... n`, with `1` as the highest
priority.

## Run database queries

Use the PostgreSQL command-line client, `psql`, from PowerShell. Connect as the
app user with the database password `todo_password`:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U todo_app_user -h localhost -d todo_app -W
```

Enter `todo_password` when prompted. You will then see a `todo_app=>` prompt.
Run SQL queries there and end each query with a semicolon. Use `\q` to exit.

Useful queries:

```sql
-- List tasks and their IDs
SELECT task_id, task_value FROM tasks ORDER BY task_id;

-- List all notes, including completion status
SELECT note_id, task_id, note_value, completed
FROM notes
ORDER BY task_id, note_id;

-- Show each task with its notes
SELECT tasks.task_id, tasks.task_value, notes.note_value, notes.completed
FROM tasks
LEFT JOIN notes ON notes.task_id = tasks.task_id
ORDER BY tasks.task_id, notes.note_id;

-- Count completed and incomplete notes
SELECT completed, COUNT(*)
FROM notes
GROUP BY completed;
```

You can also run a single query directly from PowerShell:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U todo_app_user -h localhost -d todo_app -W -c "SELECT task_id, task_value FROM tasks ORDER BY task_id;"
```

Use the `postgres` user and connect to the `postgres` database for administrator
queries, such as checking databases or roles. The `postgres` password is the
administrator password, not `todo_password`.

The app also includes a **PostgreSQL Query Executor** below the task list. Enter
a single `SELECT` query and choose **Run Query** to display the results in the
app. SQL keywords are case-insensitive, so `select ... from ...` works the same
as `SELECT ... FROM ...`. The in-app executor is read-only and displays up to
500 rows at a time; it does not allow `INSERT`, `UPDATE`, `DELETE`, or multiple
statements.

## Troubleshooting

If Python says `No module named 'dash'`:

```powershell
cd C:\Users\evanf\Code\ToDo
.\.venv\Scripts\python.exe -m pip install dash pandas psycopg[binary]
```

If PostgreSQL authentication fails, verify the local database user and password match the values in [app.py](app.py).
