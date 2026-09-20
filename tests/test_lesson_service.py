from __future__ import annotations

import pytest

from journey_tutor.ai.fake import FakeLessonGenerator
from journey_tutor.cli import build_parser, main
from journey_tutor.domain.lesson_service import LessonService
from journey_tutor.domain.models import Difficulty


async def test_lesson_service_uses_word_budget_and_generator() -> None:
    service = LessonService(FakeLessonGenerator(), words_per_minute=100)
    plan = await service.create_lesson(
        topic="gravity",
        duration_minutes=15,
        difficulty=Difficulty.BEGINNER,
    )

    assert plan.topic == "gravity"
    assert plan.duration_minutes == 15
    assert plan.difficulty == Difficulty.BEGINNER
    assert plan.word_budget == 1500
    assert plan.learning_objectives
    assert len(plan.sections) == 3
    assert sum(s.estimated_word_count for s in plan.sections) == 1500
    assert all(s.narration_script for s in plan.sections)


def test_cli_parser_lesson() -> None:
    args = build_parser().parse_args(
        ["lesson", "--topic", "gravity", "--duration", "15", "--difficulty", "beginner"]
    )
    assert args.command == "lesson"
    assert args.topic == "gravity"
    assert args.duration == 15
    assert args.difficulty == "beginner"


def test_cli_lesson_prints_summary(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "lesson",
            "--topic",
            "gravity",
            "--duration",
            "10",
            "--difficulty",
            "beginner",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Title:" in out
    assert "Word budget:" in out
    assert "Learning objectives:" in out
    assert "Sections:" in out
    assert "gravity" in out.lower() or "Gravity" in out
