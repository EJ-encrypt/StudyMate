from unittest.mock import MagicMock, patch

import pytest
import requests
from google.genai import errors

from app.services.ai.gemini_provider import _MODELS, GeminiProvider


def _api_error(code: int) -> errors.APIError:
    error = errors.APIError.__new__(errors.APIError)
    error.code = code
    error.message = f"simulated {code}"
    error.status = "UNAVAILABLE"
    error.details = {}
    return error


@pytest.fixture()
def provider() -> GeminiProvider:
    with patch("app.services.ai.gemini_provider.genai.Client"):
        return GeminiProvider()


def _response(payload: str) -> MagicMock:
    response = MagicMock()
    response.text = payload
    return response


PAYLOAD = '{"concepts": [{"name": "Deadlock", "summary": "Processes wait forever."}]}'


def test_retries_transient_error_then_succeeds(provider: GeminiProvider) -> None:
    generate = provider._client.models.generate_content
    generate.side_effect = [_api_error(503), _response(PAYLOAD)]

    with patch("app.services.ai.gemini_provider.time.sleep") as sleep:
        concepts = provider.extract_concepts("some lecture text")

    assert [c.name for c in concepts] == ["Deadlock"]
    assert generate.call_count == 2
    sleep.assert_called_once()


def test_falls_back_to_next_model_when_one_is_saturated(provider: GeminiProvider) -> None:
    generate = provider._client.models.generate_content
    # Both attempts on the first model fail, the fallback model answers.
    generate.side_effect = [_api_error(503), _api_error(503), _response(PAYLOAD)]

    with patch("app.services.ai.gemini_provider.time.sleep"):
        concepts = provider.extract_concepts("some lecture text")

    assert [c.name for c in concepts] == ["Deadlock"]
    assert generate.call_count == 3
    models_tried = [call.kwargs["model"] for call in generate.call_args_list]
    assert models_tried[0] != models_tried[2]


def test_retries_network_errors(provider: GeminiProvider) -> None:
    generate = provider._client.models.generate_content
    generate.side_effect = [requests.exceptions.ConnectionError("reset"), _response(PAYLOAD)]

    with patch("app.services.ai.gemini_provider.time.sleep"):
        concepts = provider.extract_concepts("some lecture text")

    assert [c.name for c in concepts] == ["Deadlock"]
    assert generate.call_count == 2


def test_gives_up_after_every_model_fails(provider: GeminiProvider) -> None:
    generate = provider._client.models.generate_content
    generate.side_effect = _api_error(503)

    with patch("app.services.ai.gemini_provider.time.sleep"):
        with pytest.raises(errors.APIError):
            provider.extract_concepts("some lecture text")

    assert generate.call_count == len(_MODELS) * 2


def test_does_not_retry_permanent_error(provider: GeminiProvider) -> None:
    generate = provider._client.models.generate_content
    generate.side_effect = _api_error(404)

    with patch("app.services.ai.gemini_provider.time.sleep") as sleep:
        with pytest.raises(errors.APIError):
            provider.extract_concepts("some lecture text")

    assert generate.call_count == 1
    sleep.assert_not_called()


def test_caps_concepts_at_requested_maximum(provider: GeminiProvider) -> None:
    many = ", ".join(
        f'{{"name": "C{i}", "summary": "s{i}"}}' for i in range(15)
    )
    provider._client.models.generate_content.return_value = _response(f'{{"concepts": [{many}]}}')

    concepts = provider.extract_concepts("text", max_concepts=10)

    assert len(concepts) == 10
