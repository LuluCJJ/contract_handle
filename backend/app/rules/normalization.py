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


def normalize_activity(value: str) -> str:
    text = normalize_text(value)
    if any(word in text for word in ["cancel", "cancellation", "注销", "撤销", "取消", "terminate"]):
        return "cancel"
    if any(word in text for word in ["modify", "amendment", "change", "变更", "修改"]):
        return "change"
    if any(word in text for word in ["open", "new", "apply", "开通", "新增", "申请"]):
        return "open"
    return text


def parse_amount(value: str) -> float:
    cleaned = re.sub(r"[^0-9.]", "", value)
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
