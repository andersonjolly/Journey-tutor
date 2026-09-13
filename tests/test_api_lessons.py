from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from journey_tutor.ai.fake import FakeLessonGenerator
from journey_tutor.api.deps import get_lesson_generator, get_lesson_service
from journey_tutor.config import Settings, get_settings
from journey_tutor.domain.lesson_service import LessonService
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
