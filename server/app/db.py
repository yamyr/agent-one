"""
SurrealDB connection and utilities.

RecordID notes:
- RecordID.table_name: str  (e.g., "mission")
- RecordID.id: str          (e.g., "abc123")
- str(RecordID) -> "table_name:id"
"""
from __future__ import annotations

from typing import Generator

from surrealdb import Surreal

from .config import settings


def _create_connection() -> Surreal:
    """Create a new SurrealDB connection."""
    client = Surreal(settings.surreal_url)
    client.use(settings.surreal_ns, settings.surreal_db)
    client.signin({"username": settings.surreal_user, "password": settings.surreal_pass})
    return client


def init_db():
    """Verify DB connection on startup, with retries for Railway cold starts."""
    import time as _time

    print(f"Connecting to SurrealDB: {settings.surreal_url}")
    print(f"Namespace: {settings.surreal_ns}, Database: {settings.surreal_db}")

    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        try:
            client = _create_connection()
            client.close()
            print("SurrealDB connection verified")
            return
        except Exception as exc:
            if attempt == max_attempts:
                raise RuntimeError(
                    f"Failed to connect to SurrealDB after {max_attempts} attempts"
                ) from exc
            print(f"SurrealDB not ready (attempt {attempt}/{max_attempts}): {exc}")
            _time.sleep(2)


def close_db():
    pass


def get_db() -> Generator[Surreal, None, None]:
    """Create a new connection per request."""
    client = _create_connection()
    try:
        yield client
    finally:
        client.close()


def get_db_sync() -> Surreal:
    """Get a synchronous DB connection (for background tasks)."""
    return _create_connection()


def record_id_to_str(record_id) -> str:
    """Extract string ID from SurrealDB RecordID."""
    if hasattr(record_id, "id"):
        return str(record_id.id)
    return str(record_id)
