"""Check each configured AI provider with one small real request. Run:

    python -m app.scripts.check_ai

from the backend folder, with the keys in the .env one folder up (or in the
environment). Prints which providers answer; never prints a key.
"""

import os
import sys
import time
from pathlib import Path

# The project's .env lives beside backend/, not inside it.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
if _ROOT_ENV.is_file() and not Path(".env").is_file():
    os.chdir(_ROOT_ENV.parent)

from app.core.config import settings  # noqa: E402
from app.services.ai import _KEYS, _build  # noqa: E402

SAMPLE = (
    "A functional dependency X -> Y means the value of X determines the value of Y. "
    "Second normal form removes partial dependencies on a composite key."
)


def check(name: str) -> bool:
    if name in _KEYS and not _KEYS[name]():
        print(f"  {name}: no API key set - skipped")
        return False
    provider = _build(name)
    started = time.monotonic()
    try:
        concepts = provider.extract_concepts(SAMPLE, max_concepts=3)
        vectors = provider.embed(["functional dependency", "normal form"])
    except Exception as exc:  # noqa: BLE001 -- reported, not raised
        print(f"  {name}: FAILED - {type(exc).__name__}: {str(exc)[:300]}")
        return False
    print(
        f"  {name}: OK in {time.monotonic() - started:.1f}s - "
        f"{len(concepts)} concepts ({', '.join(c.name for c in concepts)}), "
        f"{len(vectors)} embeddings of {len(vectors[0]) if vectors else 0} dimensions"
    )
    return True


def main() -> None:
    names = settings.ai_providers_list
    print(f"AI_PROVIDERS = {','.join(names)}")
    results = [check(name) for name in names]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
