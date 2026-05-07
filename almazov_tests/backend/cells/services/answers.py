import re


def normalize_answer(value: str) -> str:
    if not value:
        return ""

    value = value.strip().lower()
    value = value.replace("ё", "е")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s-]", "", value)
    return value
