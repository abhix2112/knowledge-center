"""Database connection pool and the FastAPI dependency that hands out connections."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from psycopg import Connection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

from knowledge_center.config import settings

SCHEMA_FILE = Path(__file__).parent / "schema.sql"

# A pool keeps a few connections open and reuses them, instead of opening a
# new connection for every request (opening one costs ~10-50 ms).
# dict_row makes every row come back as a dict: {"id": ..., "title": ...}.
pool = ConnectionPool(
    settings.database_url,
    kwargs={"row_factory": dict_row},
    open=False,  # opened in main.py when the app starts
)


def create_tables() -> None:
    with pool.connection() as conn:
        conn.execute(SCHEMA_FILE.read_text())


def get_conn() -> Iterator[Connection[DictRow]]:
    """One connection per request.

    `pool.connection()` commits when the request finishes normally and rolls
    back if an exception was raised, so each request is one transaction.
    """
    with pool.connection() as conn:
        yield conn


# Use this as a parameter type in endpoints: `def endpoint(conn: DbConn)`.
DbConn = Annotated[Connection[DictRow], Depends(get_conn)]
