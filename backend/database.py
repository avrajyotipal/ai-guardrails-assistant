"""
Database connection using psycopg2 with a thread-safe connection pool.
Accepts both supabase-style PostgreSQL URLs and standard DSNs.
"""

import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from config import settings

_pool: pool.ThreadedConnectionPool = None


def _parse_db_url(url: str) -> dict:
    """Parse a PostgreSQL URL that may contain @ inside the password."""
    rest = url.split("://", 1)[1]
    at_positions = [i for i, c in enumerate(rest) if c == "@"]
    last_at = at_positions[-1]
    creds   = rest[:last_at]
    host_db = rest[last_at + 1:]

    colon_pos = creds.index(":")
    user     = creds[:colon_pos]
    password = creds[colon_pos + 1:].strip("[]")   # strip Supabase template brackets

    host_port, dbname = host_db.rsplit("/", 1)
    host, port = host_port.rsplit(":", 1)

    return dict(host=host, port=int(port), dbname=dbname, user=user, password=password)


def _get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        params = _parse_db_url(settings.get_database_url())
        params["sslmode"] = "require"
        _pool = pool.ThreadedConnectionPool(minconn=1, maxconn=10, **params)
    return _pool


@contextmanager
def get_db():
    """Context manager that yields a psycopg2 connection from the pool."""
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def fetchall_as_dicts(cursor) -> list[dict]:
    """Convert cursor results to list of dicts using column names."""
    if cursor.description is None:
        return []
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def fetchone_as_dict(cursor) -> dict | None:
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))
