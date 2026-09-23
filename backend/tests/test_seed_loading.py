import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app import db
from app.main import app
from app.models import Proposal, Task, Team
from app.rating import compute_rating
from app.schemas import TaskCard


def test_startup_loads_seed_once_and_catalog_keeps_global_positions(tmp_path, monkeypatch):
    cards = db.read_seed("cards.json")
    teams = db.read_seed("teams.json")
    proposals = db.read_seed("proposals.json")
    engine = create_engine(f"sqlite:///{tmp_path / 'seed.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.chdir(tmp_path)  # Seed paths must not depend on the launch directory.
    try:
        with TestClient(app) as client:
            initial_catalog = client.get("/api/catalog")
            assert initial_catalog.status_code == 200
            assert [item["position"] for item in initial_catalog.json()] == [1, 2, 3, 4, 5]
            assert [item["rating_total"] for item in initial_catalog.json()] == [95, 81, 66, 48, 25]
            assert len(client.get("/api/examples/drafts").json()) == 5
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
def test_startup_with_missing_seed_files(tmp_path, monkeypatch, caplog, files):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    for filename in files:
        (seed_dir / filename).write_text(json.dumps(db.read_seed(filename), ensure_ascii=False), encoding="utf-8")
    engine = create_engine(f"sqlite:///{tmp_path / 'partial.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SEED_DIR", seed_dir)
    try:
        with TestClient(app) as client:
            # Never leave a partial Team marker that prevents the next load.
            assert client.get("/api/teams").json() == []
            assert client.get("/api/tasks").json() == []
            assert client.get("/api/examples/drafts").json() == []
            assert "Не удалось загрузить seed" in caplog.text
    finally:
        engine.dispose()


def test_manual_task_does_not_block_seed_and_proposals_use_seed_ids(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'manual.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    db.create_db_and_tables()
    with Session(engine) as session:
        session.add(Task(id=100, industry="IT", draft_text="Существующий ручной черновик"))
        session.commit()
    try:
        with TestClient(app) as client:
            manual = client.get("/api/tasks/100").json()
            assert manual["draft_text"] == "Существующий ручной черновик"
            assert manual["status"] == "clarifying" and manual["rating"] is None
            assert manual["proposals_count"] == 0
            assert len(client.get("/api/tasks").json()) == 6
            assert len(client.get("/api/teams").json()) == 5
            catalog = client.get("/api/catalog").json()
            assert [item["position"] for item in catalog] == [1, 2, 3, 4, 5]
            assert all(item["id"] > 100 and item["proposals_count"] == 1 for item in catalog)
            snapshot = client.get("/api/tasks").json()
        with TestClient(app) as client:
            assert client.get("/api/tasks").json() == snapshot
    finally:
        engine.dispose()


@pytest.mark.parametrize("filename,content", [
    ("cards.json", "broken JSON"),
    ("teams.json", "{}"),
    ("drafts.json", '[{"id": 1}]'),
    ("proposals.json", '[{"task_index": 99, "team_index": 0}]'),
])
def test_invalid_seed_is_logged_rolled_back_and_can_be_retried(tmp_path, monkeypatch, caplog, filename, content):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    originals = {path.name: path.read_text(encoding="utf-8") for path in db.SEED_DIR.glob("*.json")}
    for name, text in originals.items():
        (seed_dir / name).write_text(text, encoding="utf-8")
    (seed_dir / filename).write_text(content, encoding="utf-8")
    engine = create_engine(f"sqlite:///{tmp_path / 'invalid.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SEED_DIR", seed_dir)
    try:
        with TestClient(app) as client:
            assert client.get("/api/catalog").json() == []
            assert client.get("/api/teams").json() == []
            assert "Не удалось загрузить seed" in caplog.text
        (seed_dir / filename).write_text(originals[filename], encoding="utf-8")
        with TestClient(app) as client:
            assert len(client.get("/api/catalog").json()) == 5
            assert len(client.get("/api/teams").json()) == 5
    finally:
        engine.dispose()


def test_failed_reset_preserves_existing_data(tmp_path, monkeypatch, caplog):
    engine = create_engine(f"sqlite:///{tmp_path / 'reset-failure.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    db.create_db_and_tables()
    assert db.seed_database()
    with Session(engine) as session:
        before = [[row.model_dump() for row in session.exec(select(model))] for model in (Task, Team, Proposal)]
    monkeypatch.setattr(db, "SEED_DIR", tmp_path / "missing-seed")
    try:
        with pytest.raises(ValueError):
            db.reset_database()
        with Session(engine) as session:
            after = [[row.model_dump() for row in session.exec(select(model))] for model in (Task, Team, Proposal)]
        assert after == before
        assert "Сброс БД отменён" in caplog.text
    finally:
        engine.dispose()


def test_reset_command_requires_confirmation_and_reloads_seed(tmp_path):
    backend_dir = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{tmp_path / 'reset-cli.db'}"
    engine = create_engine(database_url)
    db.SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Task(industry="IT", draft_text="Ручной черновик перед тестовым сбросом"))
        session.commit()
    env = {**os.environ, "DATABASE_URL": database_url, "AI_MODE": "stub", "PYTHONIOENCODING": "utf-8"}
    try:
        cancelled = subprocess.run([sys.executable, "-m", "app.reset_db"], cwd=backend_dir, env=env,
                                   input="NO\n", capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert cancelled.returncode == 1, cancelled.stderr
        with Session(engine) as session:
            assert len(session.exec(select(Task)).all()) == 1
            assert session.exec(select(Team)).all() == []
        reset = subprocess.run([sys.executable, "-m", "app.reset_db"], cwd=backend_dir, env=env,
                               input="RESET\n", capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert reset.returncode == 0, reset.stderr
        with Session(engine) as session:
            tasks = session.exec(select(Task)).all()
            assert len(tasks) == 5 and all(task.status == "published" for task in tasks)
            assert len(session.exec(select(Team)).all()) == 5
            assert len(session.exec(select(Proposal)).all()) == 5
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
