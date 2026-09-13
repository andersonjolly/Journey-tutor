"""Lesson generation service — orchestrates domain logic and the LLM provider."""

from __future__ import annotations

import logging

from journey_tutor.ai.protocol import LessonGenerator
from journey_tutor.domain.models import Difficulty, LessonPlan, estimate_word_budget

logger = logging.getLogger(__name__)


class LessonService:
    """Creates lesson plans without embedding provider or HTTP concerns."""

    def __init__(
        self,
        generator: LessonGenerator,
        *,
        words_per_minute: int,
    ) -> None:
        self._generator = generator
        self._words_per_minute = words_per_minute

    async def create_lesson(
        self,
        *,
        topic: str,
        duration_minutes: int,
        difficulty: Difficulty,
    ) -> LessonPlan:
        word_budget = estimate_word_budget(
            duration_minutes,
            words_per_minute=self._words_per_minute,
        )
        logger.info(
            "Creating lesson topic=%r duration=%s difficulty=%s word_budget=%s",
            topic,
            duration_minutes,
            difficulty,
            word_budget,
        )
        return await self._generator.generate(
            topic=topic,
            duration_minutes=duration_minutes,
            difficulty=difficulty,
            word_budget=word_budget,
        )
