from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from journey_tutor.ai.gemini import GeminiLessonGenerator
from journey_tutor.domain.models import Difficulty, LessonPlan, LessonSection
from journey_tutor.errors import (
    LessonMalformedResponseError,
    LessonProviderAuthError,
    LessonProviderRateLimitError,
    LessonProviderTimeoutError,
    LessonProviderUnavailableError,
)


def _sample_plan() -> LessonPlan:
    return LessonPlan(
        title="Gravity basics",
        topic="gravity",
        duration_minutes=10,
        difficulty=Difficulty.BEGINNER,
        word_budget=1300,
        learning_objectives=["Explain gravity"],
        sections=[
            LessonSection(
                title="Intro",
                estimated_word_count=1300,
                narration_script="Welcome to gravity.",
            )
        ],
    )


def _api_error(cls: type[genai_errors.APIError], code: int) -> genai_errors.APIError:
    return cls(code, {"error": {"message": "boom", "status": "ERROR", "code": code}})


@pytest.fixture
def generator() -> GeminiLessonGenerator:
    with patch("journey_tutor.ai.gemini.genai.Client") as client_cls:
        client_cls.return_value = MagicMock()
        gen = GeminiLessonGenerator(api_key="test-key", model="gemini-2.5-flash")
        gen._client = MagicMock()
        return gen


async def test_gemini_returns_parsed_lesson(generator: GeminiLessonGenerator) -> None:
    plan = _sample_plan()
    response = MagicMock()
    response.parsed = plan
    generator._client.aio.models.generate_content = AsyncMock(return_value=response)

    result = await generator.generate(
        topic="gravity",
        duration_minutes=10,
        difficulty=Difficulty.BEGINNER,
        word_budget=1300,
    )
    assert result.title == "Gravity basics"


async def test_gemini_auth_error(generator: GeminiLessonGenerator) -> None:
    generator._client.aio.models.generate_content = AsyncMock(
        side_effect=_api_error(genai_errors.ClientError, 401)
    )
    with pytest.raises(LessonProviderAuthError):
        await generator.generate(
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1300,
        )


async def test_gemini_rate_limit(generator: GeminiLessonGenerator) -> None:
    generator._client.aio.models.generate_content = AsyncMock(
        side_effect=_api_error(genai_errors.ClientError, 429)
    )
    with pytest.raises(LessonProviderRateLimitError):
        await generator.generate(
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1300,
        )


async def test_gemini_server_error(generator: GeminiLessonGenerator) -> None:
    generator._client.aio.models.generate_content = AsyncMock(
        side_effect=_api_error(genai_errors.ServerError, 503)
    )
    with pytest.raises(LessonProviderUnavailableError):
        await generator.generate(
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1300,
        )


async def test_gemini_timeout(generator: GeminiLessonGenerator) -> None:
    generator._client.aio.models.generate_content = AsyncMock(
        side_effect=TimeoutError("timed out")
    )
    with pytest.raises(LessonProviderTimeoutError):
        await generator.generate(
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1300,
        )


async def test_gemini_malformed_empty(generator: GeminiLessonGenerator) -> None:
    response = MagicMock()
    response.parsed = None
    response.text = None
    generator._client.aio.models.generate_content = AsyncMock(return_value=response)
    with pytest.raises(LessonMalformedResponseError):
        await generator.generate(
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1300,
        )


async def test_gemini_malformed_invalid_json(generator: GeminiLessonGenerator) -> None:
    response = MagicMock()
    response.parsed = None
    response.text = "{not-json"
    generator._client.aio.models.generate_content = AsyncMock(return_value=response)
    with pytest.raises(LessonMalformedResponseError):
        await generator.generate(
            topic="gravity",
            duration_minutes=10,
            difficulty=Difficulty.BEGINNER,
            word_budget=1300,
        )


def test_gemini_requires_api_key() -> None:
    with pytest.raises(LessonProviderAuthError):
        GeminiLessonGenerator(api_key="  ", model="gemini-2.5-flash")


async def test_gemini_passes_schema(generator: GeminiLessonGenerator) -> None:
    response = MagicMock()
    response.parsed = _sample_plan()
    mock_generate = AsyncMock(return_value=response)
    generator._client.aio.models.generate_content = mock_generate

    await generator.generate(
        topic="gravity",
        duration_minutes=10,
        difficulty=Difficulty.BEGINNER,
        word_budget=1300,
    )
    kwargs: dict[str, Any] = mock_generate.await_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash"
    assert kwargs["config"].response_schema is LessonPlan
    assert kwargs["config"].response_mime_type == "application/json"
