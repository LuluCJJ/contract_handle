import re
from typing import Iterable


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def contains_all(text: str, expected_values: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    return all(normalize_text(value) in normalized for value in expected_values)


def line_value(text: str, anchor: str) -> str:
    prefix = normalize_text(anchor)
    for line in text.splitlines():
        if normalize_text(line).startswith(prefix.lower()):
            parts = line.split(":", 1)
            return parts[1].strip() if len(parts) == 2 else line.strip()
    return ""

