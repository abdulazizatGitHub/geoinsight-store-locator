"""
db.py — Database connection management.
Uses a simple psycopg2 connection pool (min=1, max=5).
All connections are retrieved via get_conn() and must be
returned via put_conn() after use.
"""

import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL: str = os.getenv('DATABASE_URL', '')

if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL is not set in .env')

# SimpleConnectionPool is thread-safe for single-worker Uvicorn.
_pool: pool.SimpleConnectionPool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    dsn=DATABASE_URL,
)


def get_conn() -> psycopg2.extensions.connection:
    """Borrow a connection from the pool."""
    return _pool.getconn()


def put_conn(conn: psycopg2.extensions.connection) -> None:
    """Return a connection to the pool."""
    _pool.putconn(conn)
