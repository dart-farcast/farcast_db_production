"""
FarCast DB v2 — Database Connection Client
Unified Database Client supporting Supabase Cloud PostgreSQL with Connection Pooling and Local SQLite fallback.
"""
import os
import sqlite3
import threading
from typing import Any, Optional

try:
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'auth.db'))
DATABASE_URL = os.environ.get('DATABASE_URL', '')

_pg_pool: Optional[Any] = None
_pg_pool_lock = threading.Lock()

def _get_pg_pool(db_url: str):
    """Initializes and returns a singleton ThreadedConnectionPool for PostgreSQL."""
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool
    with _pg_pool_lock:
        if _pg_pool is None and HAS_PSYCOPG2 and db_url:
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            try:
                _pg_pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=20,
                    dsn=db_url,
                    connect_timeout=5
                )
            except Exception as e:
                print(f"  [DB Pool Warning] Could not initialize PostgreSQL pool ({e}).")
                _pg_pool = None
        return _pg_pool

class DBConnection:
    """Wrapper that normalizes SQLite & PostgreSQL connections to dictionary cursor responses."""
    def __init__(self, conn, is_postgres: bool = False, pool_ref: Optional[Any] = None):
        self.conn = conn
        self.is_postgres = is_postgres
        self.pool_ref = pool_ref
        self._closed = False

    def cursor(self):
        if self.is_postgres:
            return PostgresCursorWrapper(self.conn.cursor(cursor_factory=RealDictCursor))
        return SQLiteCursorWrapper(self.conn.cursor())

    def commit(self):
        if not self._closed and self.conn:
            self.conn.commit()

    def rollback(self):
        if not self._closed and self.conn:
            try:
                self.conn.rollback()
            except Exception:
                pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.is_postgres and self.pool_ref and self.conn:
            try:
                self.pool_ref.putconn(self.conn)
            except Exception:
                try:
                    self.conn.close()
                except Exception:
                    pass
        elif self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()

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
    Returns high-performance DBConnection instance using connection pooling for Cloud Postgres
    or optimized SQLite connections.
    """
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if db_url and HAS_PSYCOPG2:
        pg_pool = _get_pg_pool(db_url)
        if pg_pool:
            try:
                conn = pg_pool.getconn()
                if conn.closed:
                    pg_pool.putconn(conn, close=True)
                    conn = pg_pool.getconn()
                return DBConnection(conn, is_postgres=True, pool_ref=pg_pool)
            except Exception as e:
                print(f"  [DB Connection Warning] PostgreSQL pool checkout error: {e}")
        else:
            try:
                conn = psycopg2.connect(db_url, connect_timeout=5)
                return DBConnection(conn, is_postgres=True)
            except Exception as e:
                print(f"  [DB Connection Warning] Failed direct connecting to Cloud PostgreSQL ({e}). Falling back to local SQLite.")

    # Fallback to local SQLite
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return DBConnection(conn, is_postgres=False)
