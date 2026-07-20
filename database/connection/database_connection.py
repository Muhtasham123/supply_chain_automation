"""
PostgreSQL connection for the ETL / schema scripts.

Credentials are read from a .env file at the project root (see .env.example) so
nothing sensitive is hardcoded. Sensible localhost defaults are used when a
variable is not set - except the password, which must be supplied via .env.

Required .env variables:

    PGHOST=localhost
    PGPORT=5432
    PGDATABASE=supply_chain_db
    PGUSER=postgres
    PGPASSWORD=your_password

This module opens a single shared connection and cursor at import time
(`connection` and `cursor`), which the schema/loader scripts import directly.
"""

import os
import psycopg2

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

connection = psycopg2.connect(
    host=os.getenv("PGHOST", "localhost"),
    database=os.getenv("PGDATABASE", "supply_chain_db"),
    user=os.getenv("PGUSER", "postgres"),
    password=os.getenv("PGPASSWORD", ""),
    port=os.getenv("PGPORT", "5432"),
)

cursor = connection.cursor()
print("Database connected successfully")
