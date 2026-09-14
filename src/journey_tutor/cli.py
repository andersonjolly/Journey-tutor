"""CLI entrypoint: ``journey-tutor lesson`` and ``journey-tutor serve``."""

from __future__ import annotations

import argparse
import asyncio
import sys

import uvicorn

from journey_tutor.ai.fake import FakeLessonGenerator
from journey_tutor.ai.gemini import GeminiLessonGenerator
from journey_tutor.config import get_settings
from journey_tutor.domain.lesson_service import LessonService
from journey_tutor.domain.models import Difficulty
from journey_tutor.errors import LessonGenerationError
from journey_tutor.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="journey-tutor",
        description="Journey Tutor — structured spoken lesson generation",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    lesson = sub.add_parser("lesson", help="Generate a lesson plan and print a summary")
    lesson.add_argument("--topic", required=True, help="Learning topic")
    lesson.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Target duration in minutes",
    )
    lesson.add_argument(
        "--difficulty",
        required=True,
        choices=[d.value for d in Difficulty],
        help="Learner difficulty level",
    )

    serve = sub.add_parser("serve", help="Run the FastAPI server (API + demo UI)")
    serve.add_argument("--host", default=None, help="Bind host (default from settings)")
    serve.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port (default from settings)",
    )
    serve.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development)",
    )

    return parser


def _build_service() -> LessonService:
    settings = get_settings()
    generator: FakeLessonGenerator | GeminiLessonGenerator
    if settings.gemini_api_key.strip():
        generator = GeminiLessonGenerator(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
    else:
        generator = FakeLessonGenerator()
    return LessonService(generator, words_per_minute=settings.words_per_minute)


def _print_lesson_summary(plan: object) -> None:
    from journey_tutor.domain.models import LessonPlan

    assert isinstance(plan, LessonPlan)
    total_est = sum(s.estimated_word_count for s in plan.sections)
    print(f"Title: {plan.title}")
    print(f"Topic: {plan.topic}")
    print(f"Duration: {plan.duration_minutes} minutes")
    print(f"Difficulty: {plan.difficulty.value}")
    print(f"Word budget: {plan.word_budget}")
    print(f"Estimated words (sections): {total_est}")
    print("Learning objectives:")
    for obj in plan.learning_objectives:
        print(f"  - {obj}")
    print("Sections:")
    for i, section in enumerate(plan.sections, start=1):
        print(f"  {i}. {section.title} ({section.estimated_word_count} words)")


async def _run_lesson(topic: str, duration: int, difficulty: str) -> int:
    service = _build_service()
    try:
        plan = await service.create_lesson(
            topic=topic,
            duration_minutes=duration,
            difficulty=Difficulty(difficulty),
        )
    except LessonGenerationError as exc:
        print(f"Error: {exc.safe_message}", file=sys.stderr)
        return 1
    _print_lesson_summary(plan)
    return 0


def _run_serve(host: str | None, port: int | None, reload: bool) -> None:
    settings = get_settings()
    uvicorn.run(
        "journey_tutor.main:app",
        host=host or settings.host,
        port=port or settings.port,
        reload=reload,
    )


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "lesson":
        return asyncio.run(
            _run_lesson(
                topic=args.topic,
                duration=args.duration,
                difficulty=args.difficulty,
            )
        )
    if args.command == "serve":
        _run_serve(host=args.host, port=args.port, reload=args.reload)
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
