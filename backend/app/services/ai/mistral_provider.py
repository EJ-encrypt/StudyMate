"""Mistral adapter: the free-tier backup behind Gemini.

Chosen because its free "Experiment" plan is the only free tier measured as
large enough for whole lecture documents (about 500K tokens a minute and 1B a
month, against Groq's 6K a minute) while also offering everything StudyMate
needs from a provider: JSON-schema structured output, an embedding model, and
image input for reading timetables.

Talks to the REST API directly with httpx rather than through an SDK: the
request shapes are small, httpx is already a dependency, and it keeps a cold
start on Vercel from paying for another SDK import.
"""

import base64
import copy
import logging
import random
import re
import time

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.services.ai.alignment import align_grades
from app.services.ai.base import (
    AIProvider,
    CourseEntry,
    ExtractedConcept,
    GeneratedItem,
    ItemDraft,
    ItemKind,
    ShortAnswerGrade,
    ShortAnswerSubmission,
    TimetableEntry,
)
from app.services.ai.prompts import (
    MAX_INPUT_CHARS,
    concept_extraction_prompt,
    course_list_prompt,
    course_summary_prompt,
    generation_prompt,
    grading_prompt,
    same_concept_prompt,
    timetable_prompt,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.mistral.ai/v1"
_EMBEDDING_MODEL = "mistral-embed"
# Mistral's document OCR model: reads a PDF or image into Markdown, writing
# equations as LaTeX, which is exactly what maths material needs.
_OCR_MODEL = "mistral-ocr-latest"
_OCR_TIMEOUT_SECONDS = 180.0
# Same reasoning as the Gemini adapter: a reply that has not come in a minute
# is not worth waiting for when the hosting limit is five.
_REQUEST_TIMEOUT_SECONDS = 60.0
_ATTEMPTS_PER_MODEL = 2
_BACKOFF_BASE_SECONDS = 2.0
# 429 is retryable here, unlike for Gemini: the free plan's limit is about one
# request per second, so a short wait genuinely frees capacity.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class MistralError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Mistral API error {status_code}: {message}")
        self.status_code = status_code


class _ConceptList(BaseModel):
    concepts: list[ExtractedConcept]


class _ItemList(BaseModel):
    items: list[ItemDraft]


class _GradeList(BaseModel):
    grades: list[ShortAnswerGrade]


class _ConceptVerdict(BaseModel):
    pair: int
    same: bool


class _VerdictList(BaseModel):
    verdicts: list[_ConceptVerdict]


class _CourseSummary(BaseModel):
    summary: str


class _Timetable(BaseModel):
    entries: list[TimetableEntry]


class _CourseList(BaseModel):
    courses: list[CourseEntry]


def strict_schema(model: type[BaseModel]) -> dict:
    """A pydantic model's JSON schema, flattened for strict structured output.

    Nested models arrive as "$ref" pointers into "$defs"; these are inlined,
    and every object is closed with additionalProperties: false and all its
    fields marked required, which strict mode expects.
    """
    raw = model.model_json_schema()
    definitions = raw.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].rsplit("/", 1)[-1]
                return resolve(copy.deepcopy(definitions[name]))
            resolved = {key: resolve(value) for key, value in node.items() if key != "title"}
            if resolved.get("type") == "object" and "properties" in resolved:
                resolved["additionalProperties"] = False
                resolved["required"] = list(resolved["properties"])
            return resolved
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(raw)


_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")


class MistralProvider(AIProvider):
    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {settings.mistral_api_key}"},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        self._models = settings.mistral_models_list

    @property
    def embedding_model_id(self) -> str:
        return f"mistral:{_EMBEDDING_MODEL}"

    def extract_concepts(
        self, text: str, max_concepts: int = 10, quantitative: bool = False
    ) -> list[ExtractedConcept]:
        parsed = self._structured(concept_extraction_prompt(text, max_concepts, quantitative), _ConceptList)
        return parsed.concepts[:max_concepts]

    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
        concepts: list[str] | None = None,
        quantitative: bool = False,
        avoid: list[str] | None = None,
    ) -> list[GeneratedItem]:
        parsed = self._structured(
            generation_prompt(source_text[:MAX_INPUT_CHARS], kind, count, concepts, quantitative, avoid),
            _ItemList,
        )
        return [item.to_item() for item in parsed.items if item.kind == kind][:count]

    def grade_short_answers(self, submissions: list[ShortAnswerSubmission]) -> list[ShortAnswerGrade]:
        if not submissions:
            return []
        parsed = self._structured(grading_prompt(submissions), _GradeList)
        return align_grades(submissions, parsed.grades)

    def summarise_course(self, course_name: str, concepts: list[tuple[str, str]]) -> str:
        return self._structured(course_summary_prompt(course_name, concepts), _CourseSummary).summary.strip()

    def are_same_concept(self, pairs: list[tuple[str, str]]) -> list[bool]:
        if not pairs:
            return []
        parsed = self._structured(same_concept_prompt(pairs), _VerdictList)
        by_number = {verdict.pair: verdict.same for verdict in parsed.verdicts}
        # Unanswered pairs stay unmerged, the recoverable direction.
        return [by_number.get(index, False) for index in range(1, len(pairs) + 1)]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        body = self._post("/embeddings", {"model": _EMBEDDING_MODEL, "input": texts})
        data = sorted(body["data"], key=lambda item: item.get("index", 0))
        vectors = [item["embedding"] for item in data]
        if len(vectors) != len(texts):
            raise ValueError(f"Asked to embed {len(texts)} texts but got {len(vectors)} vectors")
        return vectors

    def read_timetable(
        self,
        data: bytes,
        mime_type: str,
        known_courses: list[tuple[str, str]],
        extra_text: str = "",
    ) -> list[TimetableEntry]:
        if data and mime_type == "application/pdf":
            # The chat endpoint takes images, not PDFs, so a PDF timetable is
            # read as text. A scanned PDF has none; Gemini handles those.
            extra_text = (extra_text + "\n" + _pdf_text(data)).strip()
            if not extra_text:
                raise ValueError("This PDF has no readable text for the backup model")
            data = b""

        content: list[dict] = [{"type": "text", "text": timetable_prompt(known_courses, extra_text)}]
        if data:
            encoded = base64.b64encode(data).decode()
            content.insert(0, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}})
        return self._structured(content, _Timetable).entries

    def read_course_list(self, data: bytes, mime_type: str, extra_text: str = "") -> list[CourseEntry]:
        if data and mime_type == "application/pdf":
            extra_text = (extra_text + "\n" + _pdf_text(data)).strip()
            if not extra_text:
                raise ValueError("This PDF has no readable text for the backup model")
            data = b""
        content: list[dict] = [{"type": "text", "text": course_list_prompt(extra_text)}]
        if data:
            encoded = base64.b64encode(data).decode()
            content.insert(0, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}})
        return self._structured(content, _CourseList).courses

    def transcribe_document(self, data: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(data).decode()
        url = f"data:{mime_type};base64,{encoded}"
        document = (
            {"type": "document_url", "document_url": url}
            if mime_type == "application/pdf"
            else {"type": "image_url", "image_url": url}
        )
        try:
            body = self._post(
                "/ocr", {"model": _OCR_MODEL, "document": document}, timeout=_OCR_TIMEOUT_SECONDS
            )
        except httpx.TimeoutException as exc:
            raise MistralError(504, "OCR did not finish in time") from exc
        pages = sorted(body.get("pages", []), key=lambda page: page.get("index", 0))
        return "\n\n".join(page.get("markdown", "") for page in pages).strip()

    def _post(self, path: str, payload: dict, timeout: float | None = None) -> dict:
        response = self._client.post(path, json=payload, **({"timeout": timeout} if timeout else {}))
        if response.status_code >= 400:
            try:
                message = response.json().get("message") or response.text
            except ValueError:
                message = response.text
            raise MistralError(response.status_code, str(message)[:500])
        return response.json()

    def _structured(self, prompt: str | list[dict], schema: type[BaseModel]):
        """Ask for JSON matching `schema`, retrying, then falling back across models."""
        payload_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__.strip("_").lower(), "schema": strict_schema(schema), "strict": True},
        }
        last_error: Exception | None = None

        for model in self._models:
            for attempt in range(1, _ATTEMPTS_PER_MODEL + 1):
                try:
                    body = self._post(
                        "/chat/completions",
                        {
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "response_format": payload_format,
                            "temperature": 0.3,
                        },
                    )
                    content = body["choices"][0]["message"]["content"]
                    # Occasionally wrapped in a markdown fence despite JSON mode.
                    return schema.model_validate_json(_FENCE.sub("", content))
                except httpx.TimeoutException as exc:
                    last_error = exc
                    logger.warning("%s did not answer within %.0fs; falling back", model, _REQUEST_TIMEOUT_SECONDS)
                    break
                except MistralError as exc:
                    if exc.status_code not in _RETRYABLE_STATUS:
                        raise
                    last_error = exc
                    reason = f"HTTP {exc.status_code}"
                except httpx.TransportError as exc:
                    last_error = exc
                    reason = type(exc).__name__

                if attempt < _ATTEMPTS_PER_MODEL:
                    delay = _BACKOFF_BASE_SECONDS * 2 ** (attempt - 1) + random.uniform(0, 1)
                    logger.warning(
                        "%s unavailable (%s), attempt %s/%s; retrying in %.1fs",
                        model, reason, attempt, _ATTEMPTS_PER_MODEL, delay,
                    )
                    time.sleep(delay)
                else:
                    logger.warning("%s unavailable (%s); falling back", model, reason)

        raise last_error if last_error else RuntimeError("No Mistral model configured")


def _pdf_text(data: bytes) -> str:
    import tempfile
    from pathlib import Path

    from app.services.extraction import extract_text

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "timetable.pdf"
        path.write_bytes(data)
        return extract_text(str(path))
