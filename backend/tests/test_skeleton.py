from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app import db, rating
from app.main import app
from app.models import Team
from app.schemas import Task, TaskCard


def test_backend_skeleton(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SEED_DIR", tmp_path / "empty-seed")
    monkeypatch.setenv("AI_MODE", "stub")
    expected_routes = {
        ("post", "/api/tasks"), ("get", "/api/tasks"), ("get", "/api/tasks/{id}"),
        ("post", "/api/tasks/{id}/answers"), ("post", "/api/rating/preview"),
        ("put", "/api/tasks/{id}/card"), ("post", "/api/tasks/{id}/publish"),
        ("get", "/api/catalog"), ("get", "/api/industries"), ("get", "/api/examples/drafts"),
        ("get", "/api/teams"), ("get", "/api/teams/{id}/recommendations"),
        ("post", "/api/tasks/{id}/proposals"), ("get", "/api/tasks/{id}/proposals"),
        ("post", "/api/proposals/{id}/decision"), ("post", "/api/proposals/{id}/milestone"),
    }
    try:
        with TestClient(app) as client:
            assert client.get("/docs").status_code == 200
            paths = client.get("/openapi.json").json()["paths"]
            assert {(method, path) for path, methods in paths.items() for method in methods} == expected_routes
            cors = client.options("/api/tasks", headers={
                "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
            })
            assert cors.headers["access-control-allow-origin"] == "http://localhost:5173"
            assert len(client.get("/api/industries").json()) == 10
            assert client.get("/api/examples/drafts").json() == []
            assert client.get("/api/tasks/9999").status_code == 404

            for text in ["short", " " * 20, "a" * 3001]:
                response = client.post("/api/tasks", json={"draft_text": text, "industry": "IT"})
                assert response.status_code == 422
                assert isinstance(response.json()["detail"], str)

            response = client.post("/api/tasks", json={
                "draft_text": "Мы небольшая сеть кофеен в Алматы. Хотим понять причины падения продаж.",
                "industry": "HoReCa",
            })
            assert response.status_code == 200, response.text
            task = Task.model_validate(response.json())
            task_url = f"/api/tasks/{task.id}"
            assert task.status == "clarifying" and task.ai_mode == "stub"
            assert 3 <= len(task.questions) <= 5
            assert task.rating is None and task.draft_rating == rating.compute_rating(task.card)
            assert task.evidence["context"] == task.draft_text
            assert client.post(f"{task_url}/publish").status_code == 400
            assert client.post(f"{task_url}/answers", json={"answers": []}).status_code == 422
            assert client.post(f"{task_url}/answers", json={"answers": [
                {"question_id": "unknown", "answer": "Проверка вопроса"},
            ]}).status_code == 400

            answer = "  Выгрузка чеков из POS за 12 месяцев в CSV  "
            data_question = next(question for question in task.questions if question.field == "data")
            other_question = next(question for question in task.questions if question.field != "data")
            answers = [
                {"question_id": other_question.id, "answer": ""},
                {"question_id": data_question.id, "answer": answer},
            ]
            task = client.post(f"{task_url}/answers", json={"answers": answers}).json()
            assert task["status"] == "card_ready" and task["rating"] is None
            assert task["answers"] == answers
            assert task["card"]["data"] == task["evidence"]["data"] == answer.strip()
            card = task["card"]
            expected_rating = rating.compute_rating(TaskCard(**card)).model_dump()
            for invalid in [{**card, "title": "ab"}, {**card, "data": "x" * 2001}]:
                assert client.put(f"{task_url}/card", json=invalid).status_code == 422
            assert client.post("/api/rating/preview", json=card).json() == expected_rating
            assert client.get(task_url).json()["rating"] is None
            task = client.put(f"{task_url}/card", json=card).json()
            assert task["status"] == "confirmed" and task["rating"] == expected_rating
            assert len(task["rating_history"]) == 1
            task = client.post(f"{task_url}/publish").json()
            assert task["status"] == "published" and task["position"] == 1
            assert client.get("/api/catalog").json()[0]["needs_clarification"] is True

            with Session(engine) as session:
                team = Team(name="DataCats", skills=["аналитика"], technologies=["Python"])
                session.add(team)
                session.commit()
                session.refresh(team)
                team_id = team.id
            assert client.get("/api/teams").json()[0]["id"] == team_id
            assert client.get(f"/api/teams/{team_id}/recommendations").json() == []
            proposal_body = {
                "team_id": team_id, "idea": "Исследуем продажи кофеен", "plan": "Построим отчёт по дням",
                "deadline": "6 недель", "prototype_url": "https://example.com/prototype",
            }
            for invalid in [{"idea": "short"}, {"plan": "short"}, {"deadline": " "}, {"prototype_url": "ftp://example.com"}]:
                assert client.post(f"{task_url}/proposals", json={**proposal_body, **invalid}).status_code == 422
            proposal = client.post(f"{task_url}/proposals", json=proposal_body).json()
            proposal_url = f"/api/proposals/{proposal['id']}"
            assert proposal["status"] == "pending"
            assert client.post(f"{proposal_url}/milestone").status_code == 400
            assert client.post(f"{proposal_url}/decision", json={"decision": "selected"}).json()["status"] == "selected"
            assert client.post(f"{proposal_url}/milestone").json()["milestones_confirmed"] == 1
            assert client.get("/api/teams").json()[0]["points"] == 10
            assert len(client.get(f"{task_url}/proposals").json()) == 1
            assert client.get(task_url).json()["proposals_count"] == 1

            # A maximal draft must fit the AI card's smaller field limit.
            second = client.post("/api/tasks", json={"draft_text": "а" * 3000, "industry": "IT"}).json()
            second_url = f"/api/tasks/{second['id']}"
            assert len(second["card"]["context"]) == 2000
            assert client.post(f"{second_url}/proposals", json=proposal_body).status_code == 400
            data_question = next(question for question in second["questions"] if question["field"] == "data")
            second = client.post(f"{second_url}/answers", json={"answers": [
                {"question_id": data_question["id"], "answer": "Упростить анализ данных"},
            ]}).json()
            # Equal ratings keep the earlier publication ahead.
            second_card = {**card, "title": "Анализ данных IT"}
            assert client.put(f"{second_url}/card", json=second_card).status_code == 200
            assert client.post(f"{second_url}/publish").json()["position"] == 2
            assert client.get("/api/catalog?industry=IT&level=draft").json()[0]["position"] == 2

            second_card["success_criteria"] = "Рост выручки на 15% за 2 месяца"
            second = client.put(f"{second_url}/card", json=second_card).json()
            assert second["rating"]["total"] > expected_rating["total"]
            assert second["status"] == "published" and second["position"] == 1
            assert len(second["rating_history"]) == 2
            assert client.get(task_url).json()["position"] == 2
            assert len(client.get("/api/tasks").json()) == 2

        # A new application lifespan uses the same persisted SQLite records.
        with TestClient(app) as client:
            assert client.get(task_url).json()["card"]["data"] == answer.strip()
    finally:
        engine.dispose()
