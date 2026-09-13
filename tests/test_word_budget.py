from __future__ import annotations

import pytest

from journey_tutor.domain.models import estimate_word_budget


def test_estimate_word_budget_default_rate() -> None:
    assert estimate_word_budget(20) == 20 * 130


def test_estimate_word_budget_custom_rate() -> None:
    assert estimate_word_budget(10, words_per_minute=150) == 1500


def test_estimate_word_budget_rejects_invalid_duration() -> None:
    with pytest.raises(ValueError, match="duration_minutes"):
        estimate_word_budget(0)


def test_estimate_word_budget_rejects_invalid_rate() -> None:
    with pytest.raises(ValueError, match="words_per_minute"):
        estimate_word_budget(10, words_per_minute=0)
