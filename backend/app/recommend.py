"""Рекомендации задач команде (AGENTS.md §9). Только подсказка: каталог не фильтруется и ничего не назначается."""
import re

from app.schemas import CatalogItem, Recommendation, Task, Team

MIN_RATING = 40
TOP = 3
MIN_STEM = 4


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower().replace("ё", "е"))


def _stem(word: str) -> str:
    # Грубая основа без морфологии: «аналитика» → «аналити», находит «аналитику», «аналитики».
    return word[:max(MIN_STEM, len(word) - 2)]


def team_tokens(team: Team) -> list[str]:
    """Слова из интересов, навыков и технологий команды без повторов, в исходном порядке."""
    tokens: dict[str, str] = {}
    for phrase in [*team.interests, *team.skills, *team.technologies]:
        for word in _words(phrase):
            if len(word) >= MIN_STEM:
                tokens.setdefault(_stem(word), word)
    return list(tokens.values())


def task_text(task: Task) -> str:
    return " ".join([task.industry, *task.card.model_dump().values()])


def matched_tokens(tokens: list[str], text: str) -> list[str]:
    words = set(_words(text))
    return [token for token in tokens if any(word.startswith(_stem(token)) for word in words)]


def _catalog_positions(tasks: list[Task]) -> dict[int, int]:
    # Запасной расчёт места по правилу §6, если задачи пришли без position.
    published = sorted(
        (task for task in tasks if task.status == "published" and task.rating),
        key=lambda task: (-task.rating.total, task.published_at or "", task.id),
    )
    return {task.id: position for position, task in enumerate(published, start=1)}


def _catalog_item(task: Task, position: int) -> CatalogItem:
    return CatalogItem(
        id=task.id, title=task.card.title, industry=task.industry, business_name=task.business_name,
        need_short=task.card.need[:140], rating_total=task.rating.total,
        level=task.rating.level, level_label=task.rating.level_label,
        needs_clarification=task.rating.level == "draft",
        position=position, proposals_count=task.proposals_count, published_at=task.published_at or "",
    )


def recommend(team: Team, tasks: list[Task]) -> list[Recommendation]:
    """До 3 опубликованных задач с рейтингом ≥ 40, где совпадает хотя бы одно слово команды.

    Сортировка: число совпавших слов, потом рейтинг. reasons — готовая строка «совпадает: python, аналитика».
    """
    tokens = team_tokens(team)
    positions = _catalog_positions(tasks)
    scored = []
    for task in tasks:
        if task.status != "published" or task.rating is None or task.rating.total < MIN_RATING:
            continue
        matched = matched_tokens(tokens, task_text(task))
        if matched:
            scored.append((len(matched), task.rating.total, task, matched))
    scored.sort(key=lambda item: (-item[0], -item[1], positions.get(item[2].id, 0)))
    return [
        Recommendation(
            task=_catalog_item(task, task.position or positions[task.id]),
            reasons=[f"совпадает: {', '.join(matched)}"],
        )
        for _, _, task, matched in scored[:TOP]
    ]
