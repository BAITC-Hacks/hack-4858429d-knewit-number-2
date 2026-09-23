import pytest

from app.ai import stub
from app.rating import compute_rating, level_for, next_level_for
from app.schemas import Answer, TaskCard

FULL_CARD = TaskCard(
    title="Анализ продаж кофеен в будние дни",
    context="Мы сеть из шести кофеен в Алматы. Последние три месяца выручка в будние дни падает, "
            "в выходные держится на прежнем уровне, причин мы пока не понимаем.",
    need="Хотим понять, почему в будни меньше гостей, и получить план действий, который вернёт выручку.",
    users="Управляющие кофейнями и маркетолог сети, которые планируют акции и смены",
    data="Выгрузка чеков из POS за 12 месяцев в CSV и таблица акций в Excel",
    constraints="Срок 6 недель, Python, доступ к данным после подписания NDA",
    expected_result="Дашборд продаж по дням и часам по каждой кофейне и три рекомендации с оценкой эффекта на выручку",
    success_criteria="Рост выручки в будни на 15% за 2 месяца после внедрения рекомендаций",
    contact="anna@example.com",
    interaction_format="Созвон раз в неделю и чат в Telegram для быстрых вопросов",
)
CATEGORY_KEYS = ["context_need", "data", "expected_result", "success_criteria", "constraints", "users", "business_link"]


def check(rating, label_start: str):
    return next(c for cat in rating.categories for c in cat.checks if c.label.startswith(label_start))


def test_empty_card_is_zero_draft():
    rating = compute_rating(TaskCard())
    assert rating.total == 0 and rating.level == "draft"
    assert rating.level_label == "Черновик · требует уточнения"
    assert [cat.key for cat in rating.categories] == CATEGORY_KEYS
    assert [cat.max for cat in rating.categories] == [20, 20, 15, 15, 10, 10, 10]
    assert sum(item.points for item in rating.missing) == 100
    assert rating.next_level.model_dump() == {"level": "working", "label": "Рабочая", "threshold": 40, "points_needed": 40}


def test_full_card_is_100_priority():
    rating = compute_rating(FULL_CARD)
    assert rating.total == 100 and rating.level == "priority" and rating.level_label == "Приоритетная"
    assert rating.missing == [] and rating.next_level is None
    assert all(cat.earned == cat.max for cat in rating.categories)
    assert all(c.passed and c.hint is None for cat in rating.categories for c in cat.checks)


@pytest.mark.parametrize("total, level, label", [
    (0, "draft", "Черновик · требует уточнения"), (39, "draft", "Черновик · требует уточнения"),
    (40, "working", "Рабочая"), (69, "working", "Рабочая"),
    (70, "ready", "Готовая"), (89, "ready", "Готовая"),
    (90, "priority", "Приоритетная"), (100, "priority", "Приоритетная"),
])
def test_level_boundaries(total, level, label):
    assert level_for(total) == (level, label)


@pytest.mark.parametrize("total, threshold, needed", [(0, 40, 40), (39, 40, 1), (40, 70, 30), (89, 90, 1)])
def test_next_level(total, threshold, needed):
    nxt = next_level_for(total)
    assert (nxt.threshold, nxt.points_needed) == (threshold, needed)
    assert next_level_for(90) is None


def test_success_criteria_without_number_loses_7():
    card = FULL_CARD.model_copy(update={"success_criteria": "Выручка в будни заметно выросла"})
    rating = compute_rating(card)
    assert rating.total == 93
    failed = check(rating, "Критерий измеримый")
    assert not failed.passed and failed.points == 7
    assert failed.hint == "Добавьте измеримый критерий: число или процент (+7 баллов)"
    assert rating.missing[0].field == "success_criteria" and rating.missing[0].points == 7


@pytest.mark.parametrize("contact, passed", [
    ("anna@example.com", True), ("+7 701 123 45 67", True), ("@coffee_anna", True),
    ("Анна, менеджер", False), ("пишите в директ", False), ("8 701", False),
])
def test_contact_formats(contact, passed):
    rating = compute_rating(FULL_CARD.model_copy(update={"contact": contact}))
    assert check(rating, "Есть контакт").passed is passed
    assert rating.total == (100 if passed else 95)


@pytest.mark.parametrize("value", ["нет", " - ", "Не знаю", "N/A", "tbd", "?", "ok"])
def test_stop_list_is_not_filled(value):
    card = FULL_CARD.model_copy(update={"data": value, "users": value})
    rating = compute_rating(card)
    assert rating.total == 70
    assert {item.field for item in rating.missing} == {"data", "users"}


def test_missing_sorted_by_points_desc():
    points = [item.points for item in compute_rating(TaskCard(context="Продажи падают")).missing]
    assert points == sorted(points, reverse=True)


def test_demo_scenario_10_65_90():
    draft = "Мы небольшая сеть кофеен в Алматы. Продажи в будние дни падают, хотим понять почему и что делать."
    analysis = stub.analyze_draft(draft, "HoReCa")
    assert compute_rating(analysis.card).total == 10

    replies = {
        "data": "Выгрузка чеков из POS за 12 месяцев в CSV",
        "expected_result": "Дашборд продаж по дням и часам для каждой кофейни и три рекомендации, как поднять будни",
        "users": "Управляющие кофейнями и маркетолог сети",
        "contact": "anna@example.com, созвон раз в неделю",
    }
    answers = [Answer(question_id=q.id, answer=replies.get(q.field, "")) for q in analysis.questions]
    card = stub.build_card(draft, "HoReCa", analysis.questions, answers, analysis.card).card
    rating = compute_rating(card)
    assert rating.total == 65 and rating.level == "working"

    card = card.model_copy(update={
        "success_criteria": "рост выручки в будни на 15% за 2 месяца",
        "constraints": "срок 6 недель, Python, доступ к данным после NDA",
    })
    rating = compute_rating(card)
    assert rating.total == 90 and rating.level == "priority"
