"""Защита от выдуманных фактов (AGENTS.md §8): поле принимается только с цитатой из текста пользователя."""
import re
from typing import get_args

from app.ai.schemas import FieldOut
from app.schemas import CardField, Evidence, Removed

CARD_FIELDS: tuple[CardField, ...] = get_args(CardField)
MAX_FIELD = 2000
MAX_TITLE = 100
NO_EVIDENCE = "нет подтверждения в тексте пользователя"
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_supported(evidence: str | None, source: str) -> bool:
    """Цитата — подстрока источника или ≥ 70% её слов длиной ≥ 4 есть в источнике."""
    quote = normalize(evidence or "")
    if not quote:
        return False
    text = normalize(source)
    if quote in text:
        return True
    words = [word for word in quote.split() if len(word) >= 4]
    source_words = set(text.split())
    return bool(words) and sum(word in source_words for word in words) / len(words) >= 0.7


def numbers_supported(value: str, source: str) -> bool:
    """Цифры в значении должны быть в тексте пользователя: «+15% за 3 месяца» не придумываем."""
    known = {number.replace(",", ".") for number in NUMBER_RE.findall(source)}
    return all(number.replace(",", ".") in known for number in NUMBER_RE.findall(value))


def apply_guard(
    fields: dict[str, FieldOut], source: str,
) -> tuple[dict[CardField, str], Evidence, list[Removed]]:
    """Возвращает принятые значения, их цитаты и список отброшенных полей."""
    values: dict[CardField, str] = {}
    evidence: Evidence = {}
    removed: list[Removed] = []
    for field in CARD_FIELDS:
        item = fields.get(field)
        if item is None or not item.value:
            continue
        if field == "title":
            # Название может быть кратким пересказом без цитаты.
            if numbers_supported(item.value, source):
                values["title"] = item.value[:MAX_TITLE]
            continue
        if is_supported(item.evidence, source) and numbers_supported(item.value, source):
            value = item.value if field == "contact" else item.value[:1].upper() + item.value[1:]
            values[field] = value[:MAX_FIELD]
            evidence[field] = item.evidence
        else:
            removed.append(Removed(field=field, reason=NO_EVIDENCE))
    return values, evidence, removed
