"""Tests for the AI models endpoint (`GET /api/ai/models`)."""

from unittest.mock import Mock

from fastapi import FastAPI
from gigachat.models import Models
from httpx import AsyncClient
from starlette import status

from tests.ai.conftest import FAKE_MODELS_PAYLOAD


async def test_get_models_returns_gigachat_model_list(
    fastapi_app: FastAPI,
    client: AsyncClient,
    gigachat_mock: Mock,
    fake_models: Models,
) -> None:
    """`GET /api/ai/models` proxies `GigaChat.get_models()` to the caller."""

    gigachat_mock.get_models.return_value = fake_models
    url = fastapi_app.url_path_for("get_gigachat_model")

    response = await client.get(url, headers={"model": "GigaChat-2"})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["object"] == "list"
    assert [m["id"] for m in body["data"]] == [
        m["id"] for m in FAKE_MODELS_PAYLOAD["data"]
    ]
    gigachat_mock.get_models.assert_called_once_with()
