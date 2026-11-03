import logging
from functools import lru_cache

from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.fallback import FallbackProvider

logger = logging.getLogger(__name__)

_KEYS = {
    "gemini": lambda: settings.gemini_api_key,
    "openai": lambda: settings.openai_api_key,
    "mistral": lambda: settings.mistral_api_key,
}


def _build(name: str) -> AIProvider:
    if name == "gemini":
        from app.services.ai.gemini_provider import GeminiProvider

        return GeminiProvider()
    if name == "openai":
        from app.services.ai.openai_provider import OpenAIProvider

        return OpenAIProvider()
    if name == "mistral":
        from app.services.ai.mistral_provider import MistralProvider

        return MistralProvider()
    raise ValueError(f"Unknown AI provider {name!r}; expected 'gemini', 'mistral' or 'openai'")


@lru_cache
def get_ai_provider() -> AIProvider:
    """The configured provider, or a chain of them.

    AI_PROVIDERS is an ordered list: the first is used, the rest are tried
    when it fails. Always wrapped, even for a single provider, so callers see
    one type and embed_tagged is always available.
    """
    names = settings.ai_providers_list or ["gemini"]
    # A listed backup without a key would only ever fail after the primary
    # already has, adding a pointless error; leave it out and say so.
    usable = [name for name in names if name not in _KEYS or _KEYS[name]()]
    for name in set(names) - set(usable):
        logger.warning("AI provider %r is listed but has no API key; skipping it", name)
    return FallbackProvider([_build(name) for name in usable or names[:1]])
