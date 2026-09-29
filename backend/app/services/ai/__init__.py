from functools import lru_cache

from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.fallback import FallbackProvider


def _build(name: str) -> AIProvider:
    if name == "gemini":
        from app.services.ai.gemini_provider import GeminiProvider

        return GeminiProvider()
    if name == "openai":
        from app.services.ai.openai_provider import OpenAIProvider

        return OpenAIProvider()
    raise ValueError(f"Unknown AI provider {name!r}; expected 'gemini' or 'openai'")


@lru_cache
def get_ai_provider() -> AIProvider:
    """The configured provider, or a chain of them.

    AI_PROVIDERS is an ordered list: the first is used, the rest are tried
    when it fails. Always wrapped, even for a single provider, so callers see
    one type and embed_tagged is always available.
    """
    names = settings.ai_providers_list or ["gemini"]
    return FallbackProvider([_build(name) for name in names])
