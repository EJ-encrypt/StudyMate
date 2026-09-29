from unittest.mock import MagicMock, patch

import pytest
import requests
from google.genai import errors

from app.services.ai.base import ShortAnswerSubmission
from app.services.ai.gemini_provider import (
    GeminiProvider,
    _ConceptList,
    _GradeList,
    _ItemList,
)


def _api_error(code: int) -> errors.APIError:
    error = errors.APIError.__new__(errors.APIError)
    error.code = code
    error.message = f"simulated {code}"
    error.status = "UNAVAILABLE"
    error.details = {}
    return error


MODELS = ["model-a", "model-b", "model-c"]


@pytest.fixture()
def provider() -> GeminiProvider:
    with patch("app.services.ai.gemini_provider.genai.Client"):
        built = GeminiProvider()
    # Pin the model list so the tests do not depend on configuration.
    built._models = list(MODELS)
    return built


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

    assert generate.call_count == len(MODELS) * 2


def test_does_not_retry_permanent_error(provider: GeminiProvider) -> None:
    generate = provider._client.models.generate_content
    generate.side_effect = _api_error(404)

    with patch("app.services.ai.gemini_provider.time.sleep") as sleep:
        with pytest.raises(errors.APIError):
            provider.extract_concepts("some lecture text")

    assert generate.call_count == 1
    sleep.assert_not_called()


def test_response_schemas_carry_no_defaults() -> None:
    """Gemini rejects a response schema containing default values.

    Guards against a field gaining a default and silently breaking every
    generation call at runtime.
    """

    def defaults_in(schema: dict, path: str = "") -> list[str]:
        found = []
        for key, value in schema.items():
            if key == "default":
                found.append(path or "<root>")
            elif isinstance(value, dict):
                found.extend(defaults_in(value, f"{path}.{key}" if path else key))
            elif isinstance(value, list):
                for index, entry in enumerate(value):
                    if isinstance(entry, dict):
                        found.extend(defaults_in(entry, f"{path}.{key}[{index}]"))
        return found

    for schema_model in (_ConceptList, _ItemList, _GradeList):
        assert defaults_in(schema_model.model_json_schema()) == [], (
            f"{schema_model.__name__} has defaults; Gemini will reject it"
        )


def test_caps_concepts_at_requested_maximum(provider: GeminiProvider) -> None:
    many = ", ".join(
        f'{{"name": "C{i}", "summary": "s{i}"}}' for i in range(15)
    )
    provider._client.models.generate_content.return_value = _response(f'{{"concepts": [{many}]}}')

    concepts = provider.extract_concepts("text", max_concepts=10)

    assert len(concepts) == 10


GRADE_REFS = ["11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"]


def _submissions() -> list[ShortAnswerSubmission]:
    return [
        ShortAnswerSubmission(
            reference=ref,
            question=f"Q{index}",
            expected_answer=f"model {index}",
            student_answer=f"student {index}",
        )
        for index, ref in enumerate(GRADE_REFS, start=1)
    ]


def _grades_payload(references: list[str], verdicts: list[bool]) -> str:
    entries = ", ".join(
        f'{{"reference": "{ref}", "is_correct": {str(v).lower()}, "feedback": "note {i}"}}'
        for i, (ref, v) in enumerate(zip(references, verdicts), start=1)
    )
    return f'{{"grades": [{entries}]}}'


def test_matches_grades_by_reference(provider: GeminiProvider) -> None:
    provider._client.models.generate_content.return_value = _response(
        _grades_payload(GRADE_REFS, [True, False])
    )

    grades = provider.grade_short_answers(_submissions())

    assert [g.reference for g in grades] == GRADE_REFS
    assert [g.is_correct for g in grades] == [True, False]


def test_matches_grades_when_model_decorates_the_reference(provider: GeminiProvider) -> None:
    """The model echoed "[ref]" rather than "ref", which silently unmarked everything."""
    decorated = [f"[{ref}]" for ref in GRADE_REFS]
    provider._client.models.generate_content.return_value = _response(
        _grades_payload(decorated, [True, False])
    )

    grades = provider.grade_short_answers(_submissions())

    assert [g.reference for g in grades] == GRADE_REFS
    assert [g.is_correct for g in grades] == [True, False]


def test_falls_back_to_order_when_references_are_unusable(provider: GeminiProvider) -> None:
    provider._client.models.generate_content.return_value = _response(
        _grades_payload(["question one", "question two"], [False, True])
    )

    grades = provider.grade_short_answers(_submissions())

    assert [g.reference for g in grades] == GRADE_REFS
    assert [g.is_correct for g in grades] == [False, True]


def test_reports_unmarked_when_counts_do_not_line_up(provider: GeminiProvider) -> None:
    provider._client.models.generate_content.return_value = _response(
        _grades_payload(["nonsense"], [True])
    )

    grades = provider.grade_short_answers(_submissions())

    assert [g.reference for g in grades] == GRADE_REFS
    assert all(not g.is_correct for g in grades)
    assert all("unavailable" in g.feedback.lower() for g in grades)


def test_no_submissions_makes_no_call(provider: GeminiProvider) -> None:
    assert provider.grade_short_answers([]) == []
    provider._client.models.generate_content.assert_not_called()
