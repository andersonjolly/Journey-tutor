"""FastAPI application entrypoint."""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI

from journey_tutor.api.routes import lessons
from journey_tutor.config import get_settings
from journey_tutor.logging_config import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Journey Tutor",
        description=(
            "AI-powered personalised learning: generate structured lesson plans "
            "with narration scripts from a topic, duration, and difficulty."
        ),
        version="0.1.0",
    )
    app.include_router(lessons.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    logger.info("Journey Tutor app created")
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "journey_tutor.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
