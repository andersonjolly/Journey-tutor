"""Domain models and deterministic helpers for lesson planning."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


DEFAULT_WORDS_PER_MINUTE = 130


def estimate_word_budget(
    duration_minutes: int,
    words_per_minute: int = DEFAULT_WORDS_PER_MINUTE,
) -> int:
    """Estimate spoken-word budget from duration and speaking rate.

    This is deterministic domain logic — no LLM involvement.
    """
    if duration_minutes < 1:
        raise ValueError("duration_minutes must be at least 1")
    if words_per_minute < 1:
        raise ValueError("words_per_minute must be at least 1")
    return duration_minutes * words_per_minute


class LessonSection(BaseModel):
    """One ordered section of a lesson, with narration."""

    title: str = Field(description="Short section title")
    estimated_word_count: int = Field(
        ge=1,
        description="Target spoken-word count for this section",
    )
    narration_script: str = Field(
        description="Full spoken narration for this section",
    )


class LessonPlan(BaseModel):
    """Structured lesson plan produced by the lesson generator."""

    title: str = Field(description="Lesson title")
    topic: str = Field(description="Requested learning topic")
    duration_minutes: int = Field(ge=1, description="Target lesson duration")
    difficulty: Difficulty
    word_budget: int = Field(ge=1, description="Total estimated spoken-word budget")
    learning_objectives: list[str] = Field(
        min_length=1,
        description="What the learner should be able to do after the lesson",
    )
    sections: list[LessonSection] = Field(
        min_length=1,
        description="Ordered lesson sections with narration scripts",
    )
