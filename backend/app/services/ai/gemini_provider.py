import logging
import random
import time

import requests
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.core.config import settings
from app.services.ai.base import AIProvider, ExtractedConcept

logger = logging.getLogger(__name__)

# Free-tier Flash model on Google AI Studio (no billing required). Google
# retires these periodically -- gemini-2.5-flash was closed to new keys and the
# API itself pointed here. `client.models.list()` shows what a key can reach.
# Tried in order. Free-tier capacity is per-model and congestion shifts
# through the day -- measured against a live key, most Flash models returned
# 503 "high demand" while a lite variant answered fine, so a single model is
# not dependable here. `client.models.list()` shows what a key can reach.
_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
_MAX_INPUT_CHARS = 20000

# 429 = free-tier quota, 5xx = busy or flaking. All transient: without retries
# one blip permanently fails a student's upload.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_ATTEMPTS_PER_MODEL = 2
_BACKOFF_BASE_SECONDS = 2.0


class _ConceptList(BaseModel):
    concepts: list[ExtractedConcept]


class GeminiProvider(AIProvider):
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]:
        truncated = text[:_MAX_INPUT_CHARS]
        prompt = (
            f"Extract up to {max_concepts} key academic concepts from this lecture "
            "material. For each concept give a short name and a one-sentence summary "
            f"of what it means.\n\n{truncated}"
        )
        response = self._generate_with_retry(prompt)
        parsed = _ConceptList.model_validate_json(response.text)
        return parsed.concepts[:max_concepts]

    def _generate_with_retry(self, prompt: str):
        """Retry transient failures, then fall back to the next model."""
        last_error: Exception | None = None

        for model in _MODELS:
            for attempt in range(1, _ATTEMPTS_PER_MODEL + 1):
                try:
                    return self._client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=_ConceptList,
                        ),
                    )
                except errors.APIError as exc:
                    if exc.code not in _RETRYABLE_STATUS:
                        raise
                    last_error = exc
                    reason = f"HTTP {exc.code}"
                except requests.exceptions.RequestException as exc:
                    last_error = exc
                    reason = type(exc).__name__

                if attempt < _ATTEMPTS_PER_MODEL:
                    delay = _BACKOFF_BASE_SECONDS * 2 ** (attempt - 1) + random.uniform(0, 1)
                    logger.warning(
                        "%s unavailable (%s), attempt %s/%s; retrying in %.1fs",
                        model,
                        reason,
                        attempt,
                        _ATTEMPTS_PER_MODEL,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.warning("%s unavailable (%s); falling back", model, reason)

        raise last_error
