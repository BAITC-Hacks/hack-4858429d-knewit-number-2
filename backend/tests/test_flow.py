from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app import ai, db, rating
from app.main import app
from app.models import Proposal, Task as TaskRow, Team
from app.schemas import Task, TaskCard


DRAFT = {
    "draft_text": "Мы небольшая сеть кофеен в Алматы. Хотим понять причины падения продаж.",
    "industry": "HoReCa",
    "business_name": "Кофейня Пример",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'flow.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SEED_DIR", tmp_path / "empty-seed")
    monkeypatch.setenv("AI_MODE", "stub")
    try:
        with TestClient(app) as client:
            yield client
    finally:
        engine.dispose()


def test_stub_task_flow(client):
    response = client.post("/api/tasks", json=DRAFT)
    assert response.status_code == 200, response.text
    task = Task.model_validate(response.json())
    url = f"/api/tasks/{task.id}"
    assert task.status == "clarifying" and task.ai_mode == "stub"
    assert 3 <= len(task.questions) <= 5
    assert task.draft_rating == rating.compute_rating(task.card)
    assert task.rating is None and task.position is None
    assert task.evidence["context"] == DRAFT["draft_text"]
    proposal_body = {
        "team_id": 9999, "idea": "Исследуем продажи кофеен", "plan": "Построим отчёт по дням",
        "deadline": "6 недель", "prototype_url": "https://example.com/prototype",
    }
    assert client.post(f"{url}/proposals", json=proposal_body).status_code == 400

    data_question = next(question for question in task.questions if question.field == "data")
    answers = [{"question_id": data_question.id, "answer": "Выгрузка чеков за 12 месяцев в CSV"}]
    response = client.post(f"{url}/answers", json={"answers": answers})
    assert response.status_code == 200, response.text
    task = response.json()
    assert task["status"] == "card_ready" and task["rating"] is None
    assert task["answers"] == answers
    assert task["card"]["data"] == task["evidence"]["data"] == answers[0]["answer"]

    card = {**task["card"], "title": "Анализ продаж кофеен"}
    expected_rating = rating.compute_rating(TaskCard(**card)).model_dump()
    before_preview = client.get("/api/tasks").json()
    response = client.post("/api/rating/preview", json=card)
    assert response.status_code == 200 and response.json() == expected_rating
    assert client.get("/api/tasks").json() == before_preview

    response = client.put(f"{url}/card", json={**card, "title": " " * 120 + card["title"] + " "})
    assert response.status_code == 200, response.text
    confirmed = response.json()
    assert confirmed["status"] == "confirmed" and confirmed["position"] is None
    assert confirmed["card"] == card and confirmed["rating"] == expected_rating
    assert len(confirmed["rating_history"]) == 1
    assert confirmed["rating_history"][0]["total"] == expected_rating["total"]
    datetime.fromisoformat(confirmed["rating_history"][0]["at"])

    response = client.post(f"{url}/publish")
    assert response.status_code == 200, response.text
    published = response.json()
    assert published["status"] == "published" and published["position"] == 1
    assert published["rating"] == expected_rating
    datetime.fromisoformat(published["published_at"])
    assert client.post(f"{url}/publish").status_code == 400

    card["success_criteria"] = "Рост выручки в будни на 15% за 2 месяца"
    response = client.put(f"{url}/card", json=card)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["status"] == "published" and updated["position"] == 1
    assert updated["published_at"] == published["published_at"]
    assert updated["rating"] == rating.compute_rating(TaskCard(**card)).model_dump()
    assert updated["rating_history"][:-1] == confirmed["rating_history"]
    assert updated["rating_history"][-1]["total"] == updated["rating"]["total"]
    assert client.get(url).json() == updated
    assert client.get("/api/tasks").json() == [updated]

    with Session(db.engine) as session:
        teams = [Team(name="DataCats"), Team(name="Аналитики")]
        session.add_all(teams)
        session.commit()
        team_ids = [team.id for team in teams]
    assert client.post(f"{url}/proposals", json=proposal_body).status_code == 404
    proposals = []
    for team_id in team_ids:
        response = client.post(f"{url}/proposals", json={**proposal_body, "team_id": team_id})
        assert response.status_code == 200, response.text
        proposals.append(response.json())
    assert [proposal["status"] for proposal in proposals] == ["pending", "pending"]
    assert client.get(f"{url}/proposals").json() == proposals
    assert client.get(url).json()["proposals_count"] == 2
    assert client.get("/api/catalog").json()[0]["proposals_count"] == 2

    first, second = [f"/api/proposals/{proposal['id']}/decision" for proposal in proposals]
    assert client.post(first, json={"decision": "pending"}).status_code == 422
    assert client.post(first, json={"decision": "selected"}).json()["status"] == "selected"
    assert client.get(f"{url}/proposals").json()[1]["status"] == "pending"
    assert client.post(second, json={"decision": "selected"}).json()["status"] == "selected"
    assert all(proposal["status"] == "selected" for proposal in client.get(f"{url}/proposals").json())
    assert client.post(second, json={"decision": "rejected"}).json()["status"] == "rejected"
    assert [proposal["status"] for proposal in client.get(f"{url}/proposals").json()] == ["selected", "rejected"]
    assert all(team["points"] == 0 for team in client.get("/api/teams").json())
    assert client.get("/api/tasks/9999/proposals").status_code == 404
    assert client.post("/api/proposals/9999/decision", json={"decision": "selected"}).status_code == 404


def test_task_flow_validation(client):
    for draft_text in ["Слишком коротко", " " * 20, "а" * 3001]:
        response = client.post("/api/tasks", json={**DRAFT, "draft_text": draft_text})
        assert response.status_code == 422 and isinstance(response.json()["detail"], str)
    assert client.get("/api/tasks/9999").status_code == 404

    task = client.post("/api/tasks", json=DRAFT).json()
    url = f"/api/tasks/{task['id']}"
    response = client.post(f"{url}/publish")
    assert response.status_code == 400 and "подтвержд" in response.json()["detail"]
    question_id = task["questions"][0]["id"]
    for answers in [[], [{"question_id": question_id, "answer": " \t "}]]:
        response = client.post(f"{url}/answers", json={"answers": answers})
        assert response.status_code == 422 and isinstance(response.json()["detail"], str)
    response = client.post(f"{url}/answers", json={"answers": [
        {"question_id": "unknown", "answer": "Нужно улучшить анализ продаж"},
    ]})
    assert response.status_code == 400
    assert client.get(url).json() == task

    response = client.post(f"{url}/answers", json={"answers": [
        {"question_id": question_id, "answer": "Нужно улучшить анализ продаж"},
    ]})
    assert response.status_code == 200, response.text
    task = response.json()
    for invalid in [{"title": "аб"}, {"title": "а" * 121}, {"title": " " * 3}, {"data": "а" * 2001}]:
        response = client.put(f"{url}/card", json={**task["card"], **invalid})
        assert response.status_code == 422 and isinstance(response.json()["detail"], str)
    assert client.get(url).json() == task


@pytest.mark.parametrize("failure", ["timeout", "invalid_response"])
def test_ai_failures_fall_back_without_losing_user_input(client, monkeypatch, failure):
    def unavailable(*args, **kwargs):
        if failure == "timeout":
            raise TimeoutError("AI provider unavailable")
        return {"card": {"context": "а" * 2001}}

    monkeypatch.setattr(ai, "analyze_draft", unavailable)
    monkeypatch.setattr(ai, "build_card", unavailable)
    response = client.post("/api/tasks", json={**DRAFT, "draft_text": "а" * 3000})
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft["status"] == "clarifying" and draft["ai_mode"] == "stub"
    assert 3 <= len(draft["questions"]) <= 5
    assert draft["card"]["context"] == draft["evidence"]["context"] == "а" * 2000
    assert draft["rating"] is None and draft["draft_rating"] is not None
    data_question = next(question for question in draft["questions"] if question["field"] == "data")
    other_question = next(question for question in draft["questions"] if question["field"] != "data")
    answers = [
        {"question_id": data_question["id"], "answer": "Выгрузка чеков за 12 месяцев в CSV"},
        {"question_id": other_question["id"], "answer": ""},
    ]
    url = f"/api/tasks/{draft['id']}"
    response = client.post(f"{url}/answers", json={"answers": answers})
    assert response.status_code == 200, response.text
    task = response.json()
    assert task["status"] == "card_ready" and task["ai_mode"] == "stub"
    assert task["answers"] == answers and task["rating"] is None
    assert task["card"]["context"] == draft["card"]["context"]
    assert task["evidence"]["context"] == draft["evidence"]["context"]
    assert task["card"]["data"] == task["evidence"]["data"] == answers[0]["answer"]
    assert 3 <= len(task["card"]["title"]) <= 80
    assert client.get(url).json() == task


def test_task_reads_derive_global_positions_and_proposal_counts(client):
    with Session(db.engine) as session:
        rows = [
            TaskRow(
                **DRAFT, status="published", position=99, proposals_count=7,
                rating=rating.compute_rating(TaskCard()).model_dump(),
                published_at=published_at,
            )
            for published_at in ["2026-09-23T12:00:00+00:00", "2026-09-23T11:00:00+00:00"]
        ]
        rows.append(TaskRow(**DRAFT, position=99, proposals_count=7))
        team = Team(name="DataCats")
        session.add_all([*rows, team])
        session.commit()
        ids = [row.id for row in rows]
        session.add(Proposal(
            task_id=ids[0], team_id=team.id, team_name=team.name,
            idea="Исследуем продажи кофеен", plan="Построим отчёт по дням",
            deadline="6 недель", prototype_url="https://example.com/prototype",
        ))
        session.commit()

    response = client.get("/api/tasks")
    assert response.status_code == 200, response.text
    tasks = {task["id"]: task for task in response.json()}
    for id, position, count in [(ids[0], 2, 1), (ids[1], 1, 0), (ids[2], None, 0)]:
        assert tasks[id]["position"] == position
        assert tasks[id]["proposals_count"] == count
        assert client.get(f"/api/tasks/{id}").json() == tasks[id]
    with Session(db.engine) as session:
        assert all(row.position == 99 and row.proposals_count == 7 for row in session.exec(select(TaskRow)))
