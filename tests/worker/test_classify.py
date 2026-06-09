"""Tests for `_classify_with_gigachat` (Эпик 4: US-4.1, US-4.2)."""

import json

import pytest
from pydantic import ValidationError

from gritter.db.models.posts import AgeRating, Sentiment
from gritter.services.worker.__main__ import (
    ClassificationResult,
    _classify_with_gigachat,
)
from tests.worker.conftest import gigachat_returning


def test_classify_returns_parsed_result() -> None:
    """Happy path: well-formed JSON → typed `ClassificationResult`."""
    gigachat = gigachat_returning('{"sentiment": "positive", "age_rating": "0+"}')

    result = _classify_with_gigachat(gigachat, title="t", content="c")

    assert result == ClassificationResult(
        sentiment=Sentiment.positive,
        age_rating=AgeRating.AGE_0,
    )
    assert gigachat.chat.call_count == 1


def test_classify_retries_three_times_on_non_json() -> None:
    """Transient parser failures trigger tenacity's 3 retries before reraising."""
    gigachat = gigachat_returning("not a json at all")

    with pytest.raises(json.JSONDecodeError):
        _classify_with_gigachat(gigachat, title="t", content="c")
    assert gigachat.chat.call_count == 3


def test_classify_retries_then_succeeds() -> None:
    """First call fails, second succeeds — result returned, only 2 calls made."""

    gigachat = gigachat_returning("ignored")
    ok_response = gigachat.chat.return_value  # the 2nd response object
    ok_response.choices[
        0
    ].message.content = '{"sentiment": "neutral", "age_rating": "12+"}'
    gigachat.chat.side_effect = [Exception("upstream-timeout"), ok_response]

    result = _classify_with_gigachat(gigachat, title="t", content="c")

    assert result.sentiment == Sentiment.neutral
    assert result.age_rating == AgeRating.AGE_12
    assert gigachat.chat.call_count == 2


def test_classify_raises_validation_error_on_unknown_sentiment() -> None:
    """GigaChat returned valid JSON but with a sentiment that isn't in the enum."""

    gigachat = gigachat_returning('{"sentiment": "very_happy", "age_rating": "0+"}')

    with pytest.raises(ValidationError):
        _classify_with_gigachat(gigachat, title="t", content="c")


def test_classify_raises_validation_error_on_unknown_age_rating() -> None:
    """Same for an unknown age rating like '99+'."""

    gigachat = gigachat_returning('{"sentiment": "positive", "age_rating": "99+"}')

    with pytest.raises(ValidationError):
        _classify_with_gigachat(gigachat, title="t", content="c")
