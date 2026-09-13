"""Replaceable LLM provider interface for lesson generation."""

from __future__ import annotations

from typing import Protocol

from journey_tutor.domain.models import Difficulty, LessonPlan


class LessonGenerator(Protocol):
    """Provider-agnostic contract for generating a structured lesson plan."""

    async def generate(
        self,
        *,
        topic: str,
        duration_minutes: int,
        difficulty: Difficulty,
        word_budget: int,
    ) -> LessonPlan: ...
