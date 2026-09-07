"""SQLite infrastructure tests."""

from sqlalchemy import text

from backend.db.session import build_engine, build_session_factory, session_scope


def test_in_memory_sqlite_session_and_foreign_keys() -> None:
    engine = build_engine("sqlite:///:memory:")
    session_factory = build_session_factory(engine)

    with session_scope(session_factory) as session:
        assert session.scalar(text("SELECT 1")) == 1
        assert session.scalar(text("PRAGMA foreign_keys")) == 1

    engine.dispose()
