"""FastAPI dependencies shared by API routers."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.db_session_factory()
    try:
        yield session
    finally:
        session.close()
