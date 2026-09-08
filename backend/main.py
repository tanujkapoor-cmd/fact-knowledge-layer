"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend import __version__
from backend.api.router import api_router
from backend.config import Settings, get_settings
from backend.db import tables as _tables  # noqa: F401
from backend.db.base import Base
from backend.db.migrations import apply_additive_migrations
from backend.db.session import build_engine, build_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an independently configurable application instance."""

    resolved_settings = settings or get_settings()
    engine = build_engine(resolved_settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(engine)
        apply_additive_migrations(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory
    app.state.processing_status = {}
    app.include_router(api_router)
    return app


app = create_app()
