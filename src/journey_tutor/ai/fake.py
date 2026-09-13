"""Deterministic fake lesson generator for tests and local dry-runs."""

from __future__ import annotations

from journey_tutor.domain.models import Difficulty, LessonPlan, LessonSection


class FakeLessonGenerator:
    """Produces a deterministic lesson without calling a remote LLM."""

    async def generate(
        self,
        *,
        topic: str,
        duration_minutes: int,
        difficulty: Difficulty,
        word_budget: int,
    ) -> LessonPlan:
        # Distribute the budget across three sections; put remainder on the last.
        intro_words = max(1, word_budget // 4)
        body_words = max(1, word_budget // 2)
        remaining = word_budget - intro_words - body_words
        if remaining < 1:
            body_words = max(1, word_budget - intro_words - 1)
            remaining = max(1, word_budget - intro_words - body_words)
        outro_words = remaining

        return LessonPlan(
            title=f"{topic.title()} — {difficulty.value} lesson",
            topic=topic,
            duration_minutes=duration_minutes,
            difficulty=difficulty,
            word_budget=word_budget,
            learning_objectives=[
                f"Explain the core ideas of {topic}",
                f"Apply {topic} concepts at a {difficulty.value} level",
            ],
            sections=[
                LessonSection(
                    title="Introduction",
                    estimated_word_count=intro_words,
                    narration_script=(
                        f"Welcome. Today we explore {topic}. "
                        f"This {difficulty.value} lesson takes about "
                        f"{duration_minutes} minutes."
                    ),
                ),
                LessonSection(
                    title="Core ideas",
                    estimated_word_count=body_words,
                    narration_script=(
                        f"Let's unpack the main concepts of {topic}. "
                        "Pay attention to the key vocabulary and how the "
                        "pieces fit together."
                    ),
                ),
                LessonSection(
                    title="Wrap-up",
                    estimated_word_count=outro_words,
                    narration_script=(
                        f"To summarise {topic}: review the objectives, "
                        "practice one example, and note what to revisit next."
                    ),
                ),
            ],
        )
