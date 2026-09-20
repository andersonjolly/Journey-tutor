from __future__ import annotations

import os

import pytest

from journey_tutor.ai.gemini import GeminiLessonGenerator
from journey_tutor.config import Settings
from journey_tutor.domain.lesson_service import LessonService
from journey_tutor.domain.models import Difficulty
from journey_tutor.domain.validation import WORD_BUDGET_TOLERANCE_RATIO

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_AI_TESTS", "").lower() not in {"1", "true", "yes"},
    reason="Set RUN_LIVE_AI_TESTS=true to run live Gemini integration tests",
)


@pytest.mark.asyncio
async def test_live_gemini_lesson_generation() -> None:
    settings = Settings()
    if not settings.gemini_api_key.strip():
        pytest.skip("GEMINI_API_KEY is required for live AI tests")

    service = LessonService(
        GeminiLessonGenerator(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        ),
        words_per_minute=settings.words_per_minute,
    )
    plan = await service.create_lesson(
        topic="photosynthesis",
        duration_minutes=5,
        difficulty=Difficulty.BEGINNER,
    )

    assert plan.topic == "photosynthesis"
    assert plan.learning_objectives
    assert plan.sections
    total = sum(s.estimated_word_count for s in plan.sections)
    allowed = plan.word_budget * WORD_BUDGET_TOLERANCE_RATIO
    assert abs(total - plan.word_budget) <= allowed
