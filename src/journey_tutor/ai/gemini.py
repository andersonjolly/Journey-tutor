"""Google Gemini implementation of the lesson generator."""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from journey_tutor.domain.models import Difficulty, LessonPlan

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = """\
You are Journey Tutor, an expert instructional designer and narrator.
Create a clear, engaging spoken lesson plan for the given topic,
duration, and difficulty.

Rules:
- Respect the total word_budget across all sections
  (sum of section estimated_word_count ≈ word_budget).
- Write narration_script as natural spoken language for audio playback.
- Match vocabulary and depth to the requested difficulty.
- Include concrete learning objectives and ordered sections that flow.
- Do not mention that you are an AI or that this is a prompt.
"""


class GeminiLessonGenerator:
    """Generates structured LessonPlan objects via Gemini JSON schema output."""

    def __init__(self, *, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("gemini_api_key is required to use GeminiLessonGenerator")
        self._model = model
        self._client = genai.Client(api_key=api_key)

    async def generate(
        self,
        *,
        topic: str,
        duration_minutes: int,
        difficulty: Difficulty,
        word_budget: int,
    ) -> LessonPlan:
        prompt = (
            f"Topic: {topic}\n"
            f"Duration minutes: {duration_minutes}\n"
            f"Difficulty: {difficulty.value}\n"
            f"Total word budget: {word_budget}\n\n"
            "Return a complete lesson plan matching the schema."
        )
        logger.debug("Calling Gemini model=%s for topic=%r", self._model, topic)

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

        parsed = response.parsed
        if isinstance(parsed, LessonPlan):
            return parsed
        if isinstance(parsed, dict):
            return LessonPlan.model_validate(parsed)

        text = response.text
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return LessonPlan.model_validate_json(text)
