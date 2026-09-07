"""Database engine and session construction."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _is_in_memory_sqlite(database_url: str) -> bool:
    return database_url in {"sqlite://", "sqlite:///:memory:"}


def build_engine(database_url: str) -> Engine:
    """Build an engine with safe defaults for the project's SQLite workload."""

    options: dict[str, Any] = {"pool_pre_ping": True}
    is_sqlite = database_url.startswith("sqlite")

    if is_sqlite:
        options["connect_args"] = {"check_same_thread": False}
        if _is_in_memory_sqlite(database_url):
            options["poolclass"] = StaticPool

    engine = create_engine(database_url, **options)

    if is_sqlite:

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            if not _is_in_memory_sqlite(database_url):
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory; background jobs must open their own session."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield a transaction-scoped session and roll back failed work."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def database_is_available(engine: Engine) -> bool:
    """Raise on connectivity failure and return true on a successful probe."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
