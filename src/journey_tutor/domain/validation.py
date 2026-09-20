"""Deterministic post-generation validation for lesson plans.

Word-budget tolerance
---------------------
The app owns the word budget (``duration_minutes × WORDS_PER_MINUTE``).
Gemini is asked to stay near that budget, but token/word counts are
inexact. Validation therefore accepts a lesson when the sum of section
``estimated_word_count`` values is within ±``WORD_BUDGET_TOLERANCE_RATIO``
of the requested budget (default **25%**). Exact equality is not required.
"""

from __future__ import annotations

from journey_tutor.domain.models import Difficulty, LessonPlan
from journey_tutor.errors import LessonValidationError

# Relative tolerance on sum(estimated_word_count) vs word_budget.
# Documented in README; keep in sync with tests.
WORD_BUDGET_TOLERANCE_RATIO = 0.25


def validate_lesson_plan(
    plan: LessonPlan,
    *,
    topic: str,
    duration_minutes: int,
    difficulty: Difficulty,
    word_budget: int,
    tolerance_ratio: float = WORD_BUDGET_TOLERANCE_RATIO,
) -> LessonPlan:
    """Validate and normalise a generated lesson plan.

    Raises:
        LessonValidationError: if structural or budget checks fail.
    """
    if not plan.learning_objectives:
        raise LessonValidationError(
            "Lesson has no learning objectives",
            safe_message="Generated lesson is missing learning objectives.",
        )
    if any(not obj.strip() for obj in plan.learning_objectives):
        raise LessonValidationError(
            "Lesson has empty learning objective",
            safe_message="Generated lesson has an empty learning objective.",
        )
    if not plan.sections:
        raise LessonValidationError(
            "Lesson has no sections",
            safe_message="Generated lesson is missing sections.",
        )
    if not plan.title.strip():
        raise LessonValidationError(
            "Lesson title is empty",
            safe_message="Generated lesson has an empty title.",
        )

    for index, section in enumerate(plan.sections):
        if not section.title.strip():
            raise LessonValidationError(
                f"Section {index} has empty title",
                safe_message="Generated lesson has a section with an empty title.",
            )
        if not section.narration_script.strip():
            raise LessonValidationError(
                f"Section {index} has empty narration",
                safe_message=(
                    "Generated lesson has a section with an empty narration script."
                ),
            )
        if section.estimated_word_count < 1:
            raise LessonValidationError(
                f"Section {index} has invalid estimated_word_count",
                safe_message="Generated lesson has an invalid section word count.",
            )

    total_words = sum(s.estimated_word_count for s in plan.sections)
    if word_budget < 1:
        raise LessonValidationError(
            "word_budget must be at least 1",
            safe_message="Internal word budget is invalid.",
        )
    allowed_delta = word_budget * tolerance_ratio
    lower = word_budget - allowed_delta
    upper = word_budget + allowed_delta
    if total_words < lower or total_words > upper:
        raise LessonValidationError(
            (
                f"Total estimated words {total_words} outside "
                f"±{tolerance_ratio:.0%} of budget {word_budget} "
                f"(allowed {lower:.0f}–{upper:.0f})"
            ),
            safe_message=(
                "Generated lesson word counts are too far from the requested budget."
            ),
        )

    # Normalise request-owned fields so the provider cannot drift them.
    return plan.model_copy(
        update={
            "topic": topic,
            "duration_minutes": duration_minutes,
            "difficulty": difficulty,
            "word_budget": word_budget,
        }
    )
