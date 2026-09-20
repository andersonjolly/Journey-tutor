"""FastAPI dependency wiring."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from journey_tutor.ai.fake import FakeLessonGenerator
from journey_tutor.ai.gemini import GeminiLessonGenerator
from journey_tutor.ai.protocol import LessonGenerator
from journey_tutor.config import Settings, get_settings
from journey_tutor.domain.lesson_service import LessonService
from journey_tutor.errors import LessonProviderAuthError


@lru_cache
def get_lesson_generator() -> LessonGenerator:
    """Return Gemini when a key is configured; otherwise the fake provider.

    Never falls back to Fake after a live Gemini failure — only when no key
    is configured for local/offline use.
    """
    settings = get_settings()
    if settings.gemini_api_key.strip():
        try:
            return GeminiLessonGenerator(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
        except LessonProviderAuthError:
            # Invalid/empty key after strip — treat as misconfiguration, not fake.
            raise
    return FakeLessonGenerator()


def get_lesson_service(
    settings: Annotated[Settings, Depends(get_settings)],
    generator: Annotated[LessonGenerator, Depends(get_lesson_generator)],
) -> LessonService:
    return LessonService(
        generator,
        words_per_minute=settings.words_per_minute,
    )
