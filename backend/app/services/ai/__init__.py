from functools import lru_cache

from app.services.ai.base import AIProvider


@lru_cache
def get_ai_provider() -> AIProvider:
    from app.services.ai.gemini_provider import GeminiProvider

    return GeminiProvider()
