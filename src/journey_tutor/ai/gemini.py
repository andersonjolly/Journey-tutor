"""Google Gemini implementation of the lesson generator."""

from __future__ import annotations

import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import ValidationError

from journey_tutor.domain.models import Difficulty, LessonPlan
from journey_tutor.errors import (
    LessonGenerationError,
    LessonMalformedResponseError,
    LessonProviderAuthError,
    LessonProviderRateLimitError,
    LessonProviderTimeoutError,
    LessonProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Soft timeout for a single generate_content call (milliseconds).
_DEFAULT_TIMEOUT_MS = 60_000

_SYSTEM_INSTRUCTION = """\
You are Journey Tutor — a warm, expert personal tutor who teaches out loud.

Your job is to produce a structured spoken lesson the learner can follow
from start to finish. Teach; do not merely outline.

Pedagogy:
- Open with a brief hook, then a clear learning path.
- Progress from foundations to application; never jump ahead.
- Introduce each new term or idea before you use it heavily.
- Use short examples or analogies suited to the difficulty level.
- Match vocabulary and depth to beginner, intermediate, or advanced.
- End with a concise recap of the key takeaways.
- Avoid repetition and filler; stay near the target word budget.
- Duration is a hard constraint: the total of section estimated_word_count
  values must be close to the given word budget (within about 25%).
- Write narration_script as natural spoken language (complete sentences),
  ready for a narrator to read aloud.
- Do not mention that you are an AI, that this is a prompt, or the schema.
"""


class GeminiLessonGenerator:
    """Generates structured LessonPlan objects via Gemini Pydantic schema output."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_ms: int = _DEFAULT_TIMEOUT_MS,
    ) -> None:
        if not api_key.strip():
            raise LessonProviderAuthError(
                "gemini_api_key is empty",
                safe_message="AI provider API key is missing or invalid.",
            )
        self._model = model
        self._timeout_ms = timeout_ms
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )

    async def generate(
        self,
        *,
        topic: str,
        duration_minutes: int,
        difficulty: Difficulty,
        word_budget: int,
    ) -> LessonPlan:
        prompt = (
            f"Create a spoken lesson plan.\n\n"
            f"Topic: {topic}\n"
            f"Target duration (minutes): {duration_minutes}\n"
            f"Difficulty: {difficulty.value}\n"
            f"Target word budget (total across all sections): {word_budget}\n\n"
            "Return a complete lesson matching the response schema. "
            "Populate title, topic, duration_minutes, difficulty, word_budget, "
            "learning_objectives, and sections (title, estimated_word_count, "
            "narration_script). Sum of estimated_word_count ≈ word budget."
        )
        logger.debug("Calling Gemini model=%s for topic=%r", self._model, topic)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=LessonPlan,
                    temperature=0.7,
                ),
            )
        except Exception as exc:
            raise _map_provider_exception(exc) from exc

        return _parse_lesson_response(response)


def _parse_lesson_response(response: object) -> LessonPlan:
    parsed = getattr(response, "parsed", None)
    try:
        if isinstance(parsed, LessonPlan):
            return parsed
        if isinstance(parsed, dict):
            return LessonPlan.model_validate(parsed)

        text = getattr(response, "text", None)
        if not text:
            raise LessonMalformedResponseError(
                "Gemini returned an empty response",
                safe_message="AI provider returned an empty lesson response.",
            )
        return LessonPlan.model_validate_json(text)
    except (ValidationError, ValueError, TypeError) as exc:
        raise LessonMalformedResponseError(
            f"Gemini response failed schema validation: {exc}",
            safe_message="AI provider returned a malformed lesson response.",
        ) from exc


def _map_provider_exception(exc: BaseException) -> LessonGenerationError:
    """Map SDK / network errors to safe LessonGenerationError subclasses."""
    if isinstance(exc, LessonGenerationError):
        return exc

    if isinstance(exc, (TimeoutError, genai_errors.APIError)) and _is_timeout(exc):
        return LessonProviderTimeoutError(
            f"Gemini timed out: {type(exc).__name__}",
            safe_message="AI provider request timed out.",
        )

    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "code", None)
        if code in {401, 403}:
            return LessonProviderAuthError(
                f"Gemini auth error ({code})",
                safe_message="AI provider authentication failed.",
            )
        if code == 429:
            return LessonProviderRateLimitError(
                "Gemini rate limit (429)",
                safe_message="AI provider rate limit exceeded. Try again later.",
            )
        if code == 400 and _looks_like_bad_key(exc):
            return LessonProviderAuthError(
                "Gemini rejected API key",
                safe_message="AI provider API key is missing or invalid.",
            )
        return LessonProviderUnavailableError(
            f"Gemini client error ({code})",
            safe_message="AI provider rejected the request.",
        )

    if isinstance(exc, genai_errors.ServerError):
        return LessonProviderUnavailableError(
            f"Gemini server error ({getattr(exc, 'code', '?')})",
            safe_message="AI provider is temporarily unavailable.",
        )

    if isinstance(exc, genai_errors.APIError):
        return LessonProviderUnavailableError(
            f"Gemini API error ({getattr(exc, 'code', '?')})",
            safe_message="AI provider request failed.",
        )

    # httpx / transport timeouts and connection failures
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return LessonProviderTimeoutError(
            f"Gemini transport timeout: {type(exc).__name__}",
            safe_message="AI provider request timed out.",
        )
    if any(token in name for token in ("connect", "network", "remote")):
        return LessonProviderUnavailableError(
            f"Gemini network error: {type(exc).__name__}",
            safe_message="AI provider is temporarily unavailable.",
        )

    return LessonProviderUnavailableError(
        f"Unexpected Gemini failure: {type(exc).__name__}",
        safe_message="AI provider request failed.",
    )


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    return "timeout" in name or "timeout" in message or "timed out" in message


def _looks_like_bad_key(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in ("api key", "api_key", "permission", "unauthorized", "invalid")
    )
