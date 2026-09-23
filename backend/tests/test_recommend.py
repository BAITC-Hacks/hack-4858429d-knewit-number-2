import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app import db
from app.main import app

from app.rating import compute_rating
from app.recommend import clarity_reason, recommend, team_tokens
from app.schemas import Task, TaskCard, Team

SEED = Path(__file__).resolve().parents[1] / "seed"
DATACATS = Team(
    id=1, name="DataCats", interests=["аналитика", "ритейл", "продажи"],
    skills=["анализ данных", "прогнозирование", "визуализация"], technologies=["Python", "pandas", "SQL"], points=0,
)
RICH = {
    "context": "Мы сеть магазинов у дома, продажи в будни падают, аналитики у нас нет.",
    "need": "Хотим разобраться в данных о продажах.",
    "data": "Выгрузка чеков из 1С за 12 месяцев в CSV",
    "expected_result": "Дашборд продаж по дням и часам для каждого магазина и три рекомендации, как поднять выручку",
    "success_criteria": "Рост выручки на 10%",
    "constraints": "Срок 6 недель, Python",
    "users": "Управляющие магазинами и маркетолог сети",
    "contact": "shop@example.com",
    "interaction_format": "Созвон раз в неделю",
}


def make_task(id: int, industry: str = "Ритейл", status: str = "published", **fields) -> Task:
    card = TaskCard(title=f"Задача {id}", **fields)
    return Task(
        id=id, status=status, business_name=f"Компания {id}", industry=industry, draft_text="",
        questions=[], answers=[], card=card, evidence={}, removed=[], draft_rating=None,
        rating=compute_rating(card), rating_history=[], position=None, proposals_count=0, ai_mode="stub",
        created_at="2026-09-23T10:00:00", published_at=f"2026-09-23T10:{id:02d}:00" if status == "published" else None,
    )


def test_team_tokens_are_words_of_at_least_4_letters():
    assert team_tokens(DATACATS) == [
        "аналитика", "ритейл", "продажи", "анализ", "данных", "прогнозирование", "визуализация", "python", "pandas",
    ]


def test_low_rating_task_is_not_recommended():
    weak = make_task(1, context="Продажи падают, нужна аналитика", need="Хотим Python")
    assert compute_rating(weak.card).total < 40
    strong = make_task(2, **RICH)
    result = recommend(DATACATS, [weak, strong])
    assert [item.task.id for item in result] == [2]


def test_reasons_contain_matched_words():
    [item] = recommend(DATACATS, [make_task(1, **RICH)])
    assert item.reasons[0] == "совпадает: аналитика, ритейл, продажи, анализ, данных, python"
    assert item.reasons[1].startswith(("всё ясно", "придётся уточнить"))
    assert item.task.rating_total == compute_rating(TaskCard(**RICH)).total
    assert item.task.position == 1 and item.task.needs_clarification is False


def test_only_published_matches_sorted_and_top3():
    no_match = make_task(1, industry="Медицина", **{**RICH, "context": "Клиника", "need": "Меньше неявок",
                                                   "data": "Журнал записи 2025", "expected_result": "Бот",
                                                   "constraints": "Срок 4 недели", "users": "Регистратура клиники"})
    draft = make_task(2, status="confirmed", **RICH)
    fewer = make_task(3, industry="Логистика", **{**RICH, "context": "Доставки опаздывают", "need": "Хотим прогноз"})
    same_score_lower = make_task(4, **{**RICH, "success_criteria": "Выручка растёт"})
    tasks = [no_match, draft, fewer, same_score_lower, make_task(5, **RICH), make_task(6, **RICH)]
    ids = [item.task.id for item in recommend(DATACATS, tasks)]
    assert ids == [5, 6, 4]


def test_seed_catalog_for_datacats():
    teams = json.loads((SEED / "teams.json").read_text(encoding="utf-8"))
    cards = json.loads((SEED / "cards.json").read_text(encoding="utf-8"))
    datacats = Team(id=1, points=0, **next(team for team in teams if team["name"] == "DataCats"))
    tasks = [make_task(i, industry=seed["industry"], **{k: v for k, v in seed["card"].items() if k != "title"})
             for i, seed in enumerate(cards, start=1)]
    result = recommend(datacats, tasks)
    assert 1 <= len(result) <= 3
    assert result[0].task.industry == "Ритейл"
    assert all(item.task.rating_total >= 40 for item in result)
    assert all(item.reasons[0].startswith("совпадает: ") for item in result)


def test_clarity_reason_tells_what_to_ask_customer():
    full = TaskCard(**{**RICH, "context": RICH["context"] + " Раньше в будни было больше гостей, сейчас зал пустой.",
                       "success_criteria": "Рост выручки в будни на 10% за 2 месяца"})
    assert compute_rating(full).total == 100
    assert clarity_reason(compute_rating(full)) == "всё ясно без вопросов к заказчику"
    gaps = TaskCard(**{**RICH, "success_criteria": "", "constraints": ""})
    assert clarity_reason(compute_rating(gaps)) == "придётся уточнить у заказчика: контекст, критерии успеха, сроки и ограничения"


def test_recommendations_endpoint_on_seed(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'rec.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    try:
        with TestClient(app) as client:
            teams = {team["name"]: team["id"] for team in client.get("/api/teams").json()}
            catalog = {item["id"]: item for item in client.get("/api/catalog").json()}
            result = client.get(f"/api/teams/{teams['DataCats']}/recommendations").json()
            assert 1 <= len(result) <= 3
            assert result[0]["task"]["industry"] == "Ритейл"
            for item in result:
                assert item["task"] == catalog[item["task"]["id"]]  # то же место и данные, что в каталоге
                assert item["task"]["rating_total"] >= 40
                assert item["reasons"][0].startswith("совпадает: ")
                assert item["reasons"][1].startswith(("всё ясно", "придётся уточнить у заказчика: "))
            assert len(client.get("/api/catalog").json()) == 5  # каталог не фильтруется
            assert client.get("/api/teams/999/recommendations").status_code == 404
    finally:
        engine.dispose()
