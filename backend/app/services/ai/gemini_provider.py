from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings
from app.services.ai.base import AIProvider, ExtractedConcept

# Free-tier Flash model on Google AI Studio (no billing required). Google
# retires these periodically -- gemini-2.5-flash was closed to new keys and the
# API itself pointed here. `client.models.list()` shows what a key can reach.
_MODEL = "gemini-3.8-flash"
_MAX_INPUT_CHARS = 20000


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
        response = self._client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_ConceptList,
            ),
        )
        parsed = _ConceptList.model_validate_json(response.text)
        return parsed.concepts[:max_concepts]
