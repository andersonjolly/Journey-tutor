from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from journey_tutor.ai.fake import FakeLessonGenerator
from journey_tutor.api.deps import get_lesson_generator, get_lesson_service
from journey_tutor.config import Settings, get_settings
from journey_tutor.domain.lesson_service import LessonService
from journey_tutor.domain.models import Difficulty, LessonPlan, LessonSection
from journey_tutor.errors import (
    LessonProviderAuthError,
    LessonProviderRateLimitError,
    LessonProviderTimeoutError,
    LessonValidationError,
)
from journey_tutor.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    settings = Settings(gemini_api_key="", words_per_minute=130)

    def override_settings() -> Settings:
        return settings

    def override_generator() -> FakeLessonGenerator:
        return FakeLessonGenerator()

    def override_service() -> LessonService:
        return LessonService(
            FakeLessonGenerator(),
            words_per_minute=settings.words_per_minute,
        )

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_lesson_generator] = override_generator
    app.dependency_overrides[get_lesson_service] = override_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_demo_ui_served(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "Journey Tutor" in response.text
    assert 'id="lesson-form"' in response.text


async def test_create_lesson(client: AsyncClient) -> None:
    response = await client.post(
        "/lessons",
        json={
            "topic": "photosynthesis",
            "duration_minutes": 20,
            "difficulty": "beginner",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["topic"] == "photosynthesis"
    assert data["duration_minutes"] == 20
    assert data["difficulty"] == "beginner"
    assert data["word_budget"] == 2600
    assert data["title"]
    assert data["learning_objectives"]
    assert len(data["sections"]) >= 1
    assert data["sections"][0]["narration_script"]
    assert data["sections"][0]["estimated_word_count"] >= 1


async def test_create_lesson_validation_error(client: AsyncClient) -> None:
    response = await client.post(
        "/lessons",
        json={"topic": "", "duration_minutes": 20, "difficulty": "beginner"},
    )
    assert response.status_code == 422


async def test_ai_auth_error_maps_to_502() -> None:
    app = create_app()
    failing = AsyncMock(
        side_effect=LessonProviderAuthError(
            "bad key",
            safe_message="AI provider authentication failed.",
        )
    )

    class FailingGenerator:
        generate = failing

    app.dependency_overrides[get_settings] = lambda: Settings(gemini_api_key="x")
    app.dependency_overrides[get_lesson_service] = lambda: LessonService(
        FailingGenerator(),  # type: ignore[arg-type]
        words_per_minute=130,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/lessons",
            json={
                "topic": "gravity",
                "duration_minutes": 10,
                "difficulty": "beginner",
            },
        )
    assert response.status_code == 502
    body = response.json()
    assert body["detail"] == "AI provider authentication failed."
    assert "bad key" not in response.text
    assert "configured" not in response.text
    app.dependency_overrides.clear()


async def test_ai_rate_limit_maps_to_429() -> None:
    app = create_app()

    class FailingGenerator:
        async def generate(self, **kwargs: object) -> LessonPlan:
            raise LessonProviderRateLimitError(
                "429",
                safe_message="AI provider rate limit exceeded. Try again later.",
            )

    app.dependency_overrides[get_lesson_service] = lambda: LessonService(
        FailingGenerator(),  # type: ignore[arg-type]
        words_per_minute=130,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/lessons",
            json={
                "topic": "gravity",
                "duration_minutes": 10,
                "difficulty": "beginner",
            },
        )
    assert response.status_code == 429
    app.dependency_overrides.clear()


async def test_ai_timeout_maps_to_504() -> None:
    app = create_app()

    class FailingGenerator:
        async def generate(self, **kwargs: object) -> LessonPlan:
            raise LessonProviderTimeoutError(
                "timeout",
                safe_message="AI provider request timed out.",
            )

    app.dependency_overrides[get_lesson_service] = lambda: LessonService(
        FailingGenerator(),  # type: ignore[arg-type]
        words_per_minute=130,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/lessons",
            json={
                "topic": "gravity",
                "duration_minutes": 10,
                "difficulty": "beginner",
            },
        )
    assert response.status_code == 504
    app.dependency_overrides.clear()


async def test_validation_failure_maps_to_502() -> None:
    app = create_app()

    class BadBudgetGenerator:
        async def generate(self, **kwargs: object) -> LessonPlan:
            # Far outside ±25% of any normal budget.
            return LessonPlan(
                title="Bad",
                topic="gravity",
                duration_minutes=10,
                difficulty=Difficulty.BEGINNER,
                word_budget=1300,
                learning_objectives=["x"],
                sections=[
                    LessonSection(
                        title="Only",
                        estimated_word_count=1,
                        narration_script="Too short.",
                    )
                ],
            )

    app.dependency_overrides[get_lesson_service] = lambda: LessonService(
        BadBudgetGenerator(),  # type: ignore[arg-type]
        words_per_minute=130,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/lessons",
            json={
                "topic": "gravity",
                "duration_minutes": 10,
                "difficulty": "beginner",
            },
        )
    assert response.status_code == 502
    assert "word" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


async def test_no_silent_fake_fallback_when_generator_fails() -> None:
    """A configured live provider failure must surface as an HTTP error."""
    app = create_app()

    class LiveFailing:
        async def generate(self, **kwargs: object) -> LessonPlan:
            raise LessonValidationError(
                "bad",
                safe_message=(
                    "Generated lesson word counts are too far "
                    "from the requested budget."
                ),
            )

    app.dependency_overrides[get_settings] = lambda: Settings(
        gemini_api_key="configured-key"
    )
    app.dependency_overrides[get_lesson_service] = lambda: LessonService(
        LiveFailing(),  # type: ignore[arg-type]
        words_per_minute=130,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/lessons",
            json={
                "topic": "gravity",
                "duration_minutes": 10,
                "difficulty": "beginner",
            },
        )
    assert response.status_code == 502
    # Must not look like a successful fake lesson.
    assert "title" not in response.json()
    app.dependency_overrides.clear()
