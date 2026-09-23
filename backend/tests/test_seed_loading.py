import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app import db
from app.main import app
from app.models import Team
from app.rating import compute_rating
from app.schemas import TaskCard


def test_startup_loads_seed_once_and_catalog_keeps_global_positions(tmp_path, monkeypatch):
    cards = db.read_seed("cards.json")
    teams = db.read_seed("teams.json")
    proposals = db.read_seed("proposals.json")
    engine = create_engine(f"sqlite:///{tmp_path / 'seed.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    try:
        with TestClient(app) as client:
            tasks = client.get("/api/tasks").json()
            actual_teams = client.get("/api/teams").json()
            assert len(tasks) == len(cards) == 5
            assert len(actual_teams) == len(teams) == 5
            for task, seed in zip(tasks, cards):
                assert task["status"] == "published"
                assert task["card"] == seed["card"]
                assert task["rating"] == compute_rating(TaskCard(**seed["card"])).model_dump()
                assert task["rating_history"] == [{"total": task["rating"]["total"], "at": task["published_at"]}]
            for seed in proposals:
                task = tasks[seed["task_index"]]
                team = actual_teams[seed["team_index"]]
                replies = client.get(f"/api/tasks/{task['id']}/proposals").json()
                assert any(reply["team_id"] == team["id"] and reply["team_name"] == team["name"]
                           and reply["idea"] == seed["idea"] and reply["status"] == "pending" for reply in replies)
                assert len(replies) == task["proposals_count"]
            assert sum(task["proposals_count"] for task in tasks) == len(proposals)
            assert client.get("/api/examples/drafts").json() == db.read_seed("drafts.json")

            # A manual edit persists on restart and exercises the 140-character excerpt.
            task = tasks[0]
            card = {**task["card"], "need": "Упростить планирование маршрутов. " * 10}
            response = client.put(f"/api/tasks/{task['id']}/card", json=card)
            assert response.status_code == 200, response.text
            catalog = client.get("/api/catalog").json()
            assert len(catalog[0]["need_short"]) == 140
            assert [item["position"] for item in catalog] == list(range(1, len(catalog) + 1))
            assert [item["rating_total"] for item in catalog] == sorted((item["rating_total"] for item in catalog), reverse=True)
            for item in catalog:
                assert item["needs_clarification"] == (item["level"] == "draft")
                filtered = client.get("/api/catalog", params={"industry": item["industry"], "level": item["level"]}).json()
                assert item in filtered
                assert all(row["industry"] == item["industry"] and row["level"] == item["level"] for row in filtered)
            draft = client.post("/api/tasks", json={"draft_text": "Нужно разобраться в данных о продажах", "industry": "IT"})
            assert draft.status_code == 200, draft.text
            assert client.get("/api/catalog?industry=&level=").json() == catalog
            snapshot = client.get("/api/tasks").json()

        with TestClient(app) as client:
            assert client.get("/api/tasks").json() == snapshot
            assert client.get("/api/teams").json() == actual_teams
            assert client.get("/api/catalog").json() == catalog
    finally:
        engine.dispose()


@pytest.mark.parametrize("files", [(), ("teams.json",), ("cards.json",), ("proposals.json",), ("teams.json", "cards.json")])
def test_startup_with_missing_seed_files(tmp_path, monkeypatch, files):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    for filename in files:
        (seed_dir / filename).write_text(json.dumps(db.read_seed(filename), ensure_ascii=False), encoding="utf-8")
    engine = create_engine(f"sqlite:///{tmp_path / 'partial.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SEED_DIR", seed_dir)
    try:
        with TestClient(app) as client:
            assert len(client.get("/api/teams").json()) == (5 if "teams.json" in files else 0)
            tasks = client.get("/api/tasks").json()
            assert len(tasks) == (5 if "cards.json" in files else 0)
            assert all(task["proposals_count"] == 0 for task in tasks)
            assert client.get("/api/examples/drafts").json() == []
    finally:
        engine.dispose()


def test_seed_does_not_change_an_existing_database(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'existing.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    db.create_db_and_tables()
    with Session(engine) as session:
        session.add(Team(name="Своя команда", points=30))
        session.commit()
    try:
        with TestClient(app) as client:
            teams = client.get("/api/teams").json()
            assert len(teams) == 1 and teams[0]["name"] == "Своя команда" and teams[0]["points"] == 30
            assert client.get("/api/tasks").json() == []
    finally:
        engine.dispose()
