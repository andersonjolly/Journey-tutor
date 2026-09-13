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


@lru_cache
def get_lesson_generator() -> LessonGenerator:
    settings = get_settings()
    if settings.gemini_api_key:
        return GeminiLessonGenerator(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
    return FakeLessonGenerator()


def get_lesson_service(
    settings: Annotated[Settings, Depends(get_settings)],
    generator: Annotated[LessonGenerator, Depends(get_lesson_generator)],
) -> LessonService:
    return LessonService(
        generator,
        words_per_minute=settings.words_per_minute,
    )
