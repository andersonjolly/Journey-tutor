"""HTTP request/response schemas for the public API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from journey_tutor.domain.models import Difficulty, LessonSection


class CreateLessonRequest(BaseModel):
    topic: str = Field(
        min_length=1,
        max_length=200,
        description="Subject the learner wants to study",
        examples=["photosynthesis"],
    )
    duration_minutes: int = Field(
        ge=1,
        le=120,
        description="Target lesson length in minutes",
        examples=[20],
    )
    difficulty: Difficulty = Field(
        description="Learner difficulty level",
        examples=["beginner"],
    )


class CreateLessonResponse(BaseModel):
    title: str
    topic: str
    duration_minutes: int
    difficulty: Difficulty
    word_budget: int
    learning_objectives: list[str]
    sections: list[LessonSection]
