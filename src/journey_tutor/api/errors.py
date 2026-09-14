"""Map domain/AI errors to safe HTTP responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from journey_tutor.errors import (
    LessonGenerationError,
    LessonMalformedResponseError,
    LessonProviderAuthError,
    LessonProviderRateLimitError,
    LessonProviderTimeoutError,
    LessonProviderUnavailableError,
    LessonValidationError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LessonGenerationError)
    async def lesson_generation_error_handler(
        request: Request,
        exc: LessonGenerationError,
    ) -> JSONResponse:
        status_code = _status_for(exc)
        # Log internals; never echo secrets or raw provider dumps to clients.
        logger.warning(
            "Lesson generation failed path=%s type=%s detail=%s",
            request.url.path,
            type(exc).__name__,
            str(exc),
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": exc.safe_message,
                "error": type(exc).__name__,
            },
        )


def _status_for(exc: LessonGenerationError) -> int:
    if isinstance(exc, LessonProviderAuthError):
        return 502
    if isinstance(exc, LessonProviderRateLimitError):
        return 429
    if isinstance(exc, LessonProviderTimeoutError):
        return 504
    if isinstance(exc, (LessonMalformedResponseError, LessonValidationError)):
        return 502
    if isinstance(exc, LessonProviderUnavailableError):
        return 503
    return 502
