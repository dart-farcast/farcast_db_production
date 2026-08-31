"""
FarCast DB v2 — Database Connection Client
Unified Database Client supporting Supabase Cloud PostgreSQL and Local SQLite fallback.
"""
import os
import sqlite3
from typing import Any
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'auth.db'))
DATABASE_URL = os.environ.get('DATABASE_URL', '')

class DBConnection:
    """Wrapper that normalizes SQLite & PostgreSQL connections to dictionary cursor responses."""
    def __init__(self, conn, is_postgres: bool = False):
        self.conn = conn
        self.is_postgres = is_postgres

    def cursor(self):
        if self.is_postgres:
            return PostgresCursorWrapper(self.conn.cursor(cursor_factory=RealDictCursor))
        return SQLiteCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query: str, params: tuple = ()):
        # Convert %s or postgres placeholder to ? for sqlite
        sqlite_query = query.replace('%s', '?').replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP')
        return self.cursor.execute(sqlite_query, params)

    def fetchone(self):
        res = self.cursor.fetchone()
        return dict(res) if res else None

    def fetchall(self):
        return [dict(r) for r in self.cursor.fetchall()]

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query: str, params: tuple = ()):
        # Convert SQLite AUTOINCREMENT or ? placeholders if needed
        pg_query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY').replace('?', '%s')
        return self.cursor.execute(pg_query, params)

    def fetchone(self):
        res = self.cursor.fetchone()
        return dict(res) if res else None

    def fetchall(self):
        return [dict(r) for r in self.cursor.fetchall()]

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def lastrowid(self):
        try:
            return self.cursor.lastrowid
        except Exception:
            return None

def get_db_connection() -> DBConnection:
    """
    Returns DBConnection instance.
    Prefers Supabase Cloud PostgreSQL if DATABASE_URL is configured; otherwise uses SQLite.
    """
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if db_url and HAS_PSYCOPG2:
        try:
            conn = psycopg2.connect(db_url, connect_timeout=10)
            return DBConnection(conn, is_postgres=True)
        except Exception as e:
            print(f"  [DB Connection Warning] Failed connecting to Cloud PostgreSQL ({e}). Falling back to local SQLite.")

    # Fallback to local SQLite
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return DBConnection(conn, is_postgres=False)
