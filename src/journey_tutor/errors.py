"""Shared application errors for lesson generation.

HTTP layers map these to safe client-facing responses. Never put secrets
or raw provider payloads in ``safe_message``.
"""

from __future__ import annotations


class LessonGenerationError(Exception):
    """Base class for lesson generation failures."""

    def __init__(self, message: str, *, safe_message: str | None = None) -> None:
        super().__init__(message)
        self.safe_message = safe_message or message


class LessonProviderAuthError(LessonGenerationError):
    """Missing, invalid, or unauthorized API credentials."""


class LessonProviderRateLimitError(LessonGenerationError):
    """Provider rejected the request due to rate limiting."""


class LessonProviderTimeoutError(LessonGenerationError):
    """Provider call timed out."""


class LessonProviderUnavailableError(LessonGenerationError):
    """Provider is temporarily unavailable (server errors, network)."""


class LessonMalformedResponseError(LessonGenerationError):
    """Provider returned a response that could not be parsed into a lesson."""


class LessonValidationError(LessonGenerationError):
    """Generated lesson failed deterministic post-generation checks."""
