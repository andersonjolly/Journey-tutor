"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from journey_tutor.api.errors import register_exception_handlers
from journey_tutor.api.routes import lessons
from journey_tutor.config import get_settings
from journey_tutor.logging_config import configure_logging

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Journey Tutor",
        description=(
            "AI-powered personalised learning: generate structured lesson plans "
            "with narration scripts from a topic, duration, and difficulty."
        ),
        version="0.2.0",
    )
    register_exception_handlers(app)
    app.include_router(lessons.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        async def demo_ui() -> FileResponse:
            return FileResponse(_STATIC_DIR / "index.html")

    logger.info("Journey Tutor app created")
    return app


app = create_app()


def run() -> None:
    """Backward-compatible entry: start the server (prefer ``journey-tutor serve``)."""
    from journey_tutor.cli import main

    raise SystemExit(main(["serve"]))


if __name__ == "__main__":
    run()
