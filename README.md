# PostgreSQL Connection Setup

Connects to a PostgreSQL server running on `localhost:5432` using Python + [psycopg 3](https://www.psycopg.org/).

## Files

| File                 | Purpose                                                        |
| -------------------- | ------------------------------------------------------------- |
| `.env`               | Your real connection settings (git-ignored — **edit this**).  |
| `.env.example`       | Template showing the required variables.                       |
| `db.py`              | Connection helper: `get_connection()` and `query()`.          |
| `test_connection.py` | Verifies the connection and prints server info.               |
| `requirements.txt`   | Python dependencies.                                           |
| `venv/`              | Virtual environment with dependencies installed.              |

## One-time setup (already done)

The virtual environment was created and dependencies installed:

```powershell
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt
```

## Configure credentials

Edit `.env` and set your real database name, username, and password:

```
PGHOST=localhost
PGPORT=5432
PGDATABASE=your_database_name
PGUSER=your_username
PGPASSWORD=your_password
PGSSLMODE=prefer
```

## Test the connection

```powershell
./venv/Scripts/python.exe test_connection.py
```

A successful run prints the server version, database, and user.

## Use it in your own code

```python
from db import get_connection, query

# Simple SELECT
rows = query("SELECT * FROM my_table WHERE id = %s", (1,))

# Full control (transactions, inserts, etc.)
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO t (name) VALUES (%s)", ("hi",))
    conn.commit()
```
