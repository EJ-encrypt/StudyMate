from pathlib import Path


def extract_text_from_notes(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")
