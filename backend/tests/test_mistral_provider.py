import json
from unittest.mock import patch

import httpx
import pytest

from app.services.ai import mistral_provider as mistral_module
from app.services.ai.base import ItemKind, ShortAnswerSubmission
from app.services.ai.mistral_provider import MistralError, MistralProvider, _ItemList, strict_schema


def _provider(handler) -> MistralProvider:
    provider = MistralProvider()
    provider._client = httpx.Client(
        base_url="https://api.mistral.ai/v1", transport=httpx.MockTransport(handler)
    )
    provider._models = ["model-a", "model-b"]
    return provider


def _chat(payload: dict) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}}]})


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(mistral_module.time, "sleep", lambda _: None)


def test_strict_schema_inlines_nested_models_and_closes_objects() -> None:
    schema = strict_schema(_ItemList)
    assert "$defs" not in json.dumps(schema)
    item = schema["properties"]["items"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {"kind", "question", "working", "answer", "options", "explanation", "concept"}
    assert "mcq" in item["properties"]["kind"]["enum"]


def test_extract_concepts_sends_a_json_schema_request() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return _chat({"concepts": [{"name": "Deadlock", "summary": "Circular waiting."}]})

    concepts = _provider(handler).extract_concepts("lecture text")

    assert [c.name for c in concepts] == ["Deadlock"]
    assert seen["path"] == "/v1/chat/completions"
    assert seen["body"]["model"] == "model-a"
    assert seen["body"]["response_format"]["type"] == "json_schema"
    assert seen["body"]["response_format"]["json_schema"]["strict"] is True


def test_tolerates_a_markdown_fence_around_the_json() -> None:
    fence = "`" * 3

    def handler(request):
        content = f'{fence}json\n{{"summary": "Normal forms."}}\n{fence}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    assert _provider(handler).summarise_course("CS302", [("2NF", "x")]) == "Normal forms."


def test_rate_limit_is_retried_then_falls_back_to_the_next_model() -> None:
    models = []

    def handler(request):
        model = json.loads(request.content)["model"]
        models.append(model)
        if model == "model-a":
            return httpx.Response(429, json={"message": "rate limited"})
        return _chat({"summary": "ok"})

    assert _provider(handler).summarise_course("c", []) == "ok"
    assert models == ["model-a", "model-a", "model-b"]


def test_timeout_skips_straight_to_the_next_model() -> None:
    models = []

    def handler(request):
        model = json.loads(request.content)["model"]
        models.append(model)
        if model == "model-a":
            raise httpx.ReadTimeout("slow", request=request)
        return _chat({"summary": "ok"})

    _provider(handler).summarise_course("c", [])
    assert models == ["model-a", "model-b"]


def test_a_bad_request_is_not_retried() -> None:
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(400, json={"message": "invalid schema"})

    with pytest.raises(MistralError, match="invalid schema"):
        _provider(handler).summarise_course("c", [])
    assert len(calls) == 1


def test_generated_items_of_the_wrong_kind_are_dropped() -> None:
    item = {"question": "Q", "working": "", "answer": "A", "options": [], "explanation": "", "concept": ""}

    def handler(request):
        return _chat({"items": [{**item, "kind": "mcq"}, {**item, "kind": "flashcard"}]})

    items = _provider(handler).generate_assessment_items("text", ItemKind.FLASHCARD, count=5)
    assert [i.kind for i in items] == [ItemKind.FLASHCARD]


def test_grades_are_matched_back_to_submissions() -> None:
    def handler(request):
        return _chat({"grades": [{"reference": "a1", "is_correct": True, "feedback": "Good."}]})

    grades = _provider(handler).grade_short_answers(
        [ShortAnswerSubmission(reference="a1", question="q", expected_answer="e", student_answer="s")]
    )
    assert grades[0].is_correct is True


def test_embed_returns_one_vector_per_text_in_order() -> None:
    def handler(request):
        assert request.url.path == "/v1/embeddings"
        return httpx.Response(
            200, json={"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]}
        )

    provider = _provider(handler)
    assert provider.embed(["a", "b"]) == [[1.0], [2.0]]
    assert provider.embedding_model_id == "mistral:mistral-embed"


def test_embed_rejects_a_short_response() -> None:
    def handler(request):
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0]}]})

    with pytest.raises(ValueError, match="2 texts but got 1"):
        _provider(handler).embed(["a", "b"])


def test_timetable_image_is_sent_as_a_data_url() -> None:
    seen = {}

    def handler(request):
        seen["content"] = json.loads(request.content)["messages"][0]["content"]
        return _chat(
            {
                "entries": [
                    {"title": "Databases", "course_code": "CS302", "day_of_week": 0,
                     "start_time": "08:30", "end_time": "10:30", "venue": "JQB"}
                ]
            }
        )

    entries = _provider(handler).read_timetable(b"\x89PNG", "image/png", [("CS302", "Databases")])
    assert entries[0].title == "Databases"
    assert seen["content"][0]["type"] == "image_url"
    assert seen["content"][0]["image_url"]["url"].startswith("data:image/png;base64,")


def test_a_scanned_pdf_timetable_is_refused_rather_than_sent() -> None:
    def handler(request):  # pragma: no cover - must not be called
        raise AssertionError("no request expected")

    with patch.object(mistral_module, "_pdf_text", return_value=""):
        with pytest.raises(ValueError, match="no readable text"):
            _provider(handler).read_timetable(b"%PDF", "application/pdf", [])


def test_a_listed_provider_without_a_key_is_skipped(monkeypatch) -> None:
    from app.core.config import settings
    from app.services import ai

    monkeypatch.setattr(settings, "ai_providers", "gemini,mistral")
    monkeypatch.setattr(settings, "gemini_api_key", "g-key")
    monkeypatch.setattr(settings, "mistral_api_key", "")
    ai.get_ai_provider.cache_clear()
    try:
        chain = ai.get_ai_provider()
        assert [type(p).__name__ for p in chain._providers] == ["GeminiProvider"]
    finally:
        ai.get_ai_provider.cache_clear()


def test_mistral_failures_get_student_facing_messages() -> None:
    from app.services.failures import describe

    message, can_retry = describe(MistralError(429, "x"))
    assert can_retry is True
    assert "usage limit" in message
    assert describe(MistralError(401, "x"))[1] is False
