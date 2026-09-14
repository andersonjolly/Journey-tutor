from __future__ import annotations

import pytest

from journey_tutor.domain.models import Difficulty, LessonPlan, LessonSection
from journey_tutor.domain.validation import (
    WORD_BUDGET_TOLERANCE_RATIO,
    validate_lesson_plan,
)
from journey_tutor.errors import LessonValidationError


def _plan(*, word_counts: list[int], budget: int = 1000) -> LessonPlan:
    return LessonPlan(
        title="Test lesson",
        topic="gravity",
        duration_minutes=10,
        difficulty=Difficulty.BEGINNER,
        word_budget=budget,
        learning_objectives=["Explain gravity"],
        sections=[
            LessonSection(
                title=f"Section {i}",
                estimated_word_count=count,
                narration_script=f"Narration for section {i}.",
            )
            for i, count in enumerate(word_counts, start=1)
        ],
    )


def test_validate_accepts_exact_budget() -> None:
    plan = validate_lesson_plan(
        _plan(word_counts=[250, 500, 250], budget=1000),
        topic="gravity",
        duration_minutes=10,
        difficulty=Difficulty.BEGINNER,
        word_budget=1000,
    )
    assert plan.word_budget == 1000
    assert plan.topic == "gravity"


def test_validate_accepts_within_tolerance() -> None:
    # 25% of 1000 = 250 → 750–1250 allowed
    assert WORD_BUDGET_TOLERANCE_RATIO == 0.25
    plan = validate_lesson_plan(
        _plan(word_counts=[800], budget=999),
        topic="gravity",
        duration_minutes=10,
        difficulty=Difficulty.BEGINNER,
        word_budget=1000,
    )
    assert plan.word_budget == 1000  # normalised to request


def test_validate_rejects_outside_tolerance() -> None:
    with pytest.raises(LessonValidationError, match="outside"):
        validate_lesson_plan(
            _plan(word_counts=[100], budget=1000),
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1000,
        )


def test_validate_rejects_empty_narration() -> None:
    plan = _plan(word_counts=[1000], budget=1000)
    plan.sections[0].narration_script = "   "
    with pytest.raises(LessonValidationError, match="empty narration"):
        validate_lesson_plan(
            plan,
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1000,
        )


def test_validate_rejects_empty_objectives() -> None:
    plan = _plan(word_counts=[1000], budget=1000)
    plan.learning_objectives = ["  "]
    with pytest.raises(LessonValidationError, match="empty learning objective"):
        validate_lesson_plan(
            plan,
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1000,
        )


def test_validate_normalises_request_fields() -> None:
    plan = _plan(word_counts=[1000], budget=50)
    plan.topic = "wrong"
    plan.difficulty = Difficulty.ADVANCED
    plan.duration_minutes = 99
    out = validate_lesson_plan(
        plan,
        topic="photosynthesis",
        duration_minutes=10,
        difficulty=Difficulty.INTERMEDIATE,
        word_budget=1000,
    )
    assert out.topic == "photosynthesis"
    assert out.duration_minutes == 10
    assert out.difficulty == Difficulty.INTERMEDIATE
    assert out.word_budget == 1000
