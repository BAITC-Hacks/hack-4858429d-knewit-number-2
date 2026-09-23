import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, select

from app import models  # Register tables before create_all.
from app.rating import compute_rating
from app.schemas import ProposalCreate, TaskCard

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
engine = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///./app.db"),
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def read_seed(filename: str) -> list[dict]:
    path = SEED_DIR / filename
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def seed_database() -> None:
    # Routers import get_session, so reuse catalog ordering after modules are loaded.
    from app.routers.catalog import update_positions

    with Session(engine) as session:
        if any(session.exec(select(model.id).limit(1)).first() is not None
               for model in (models.Task, models.Team, models.Proposal)):
            return

        teams = [models.Team.model_validate(item) for item in read_seed("teams.json")]
        tasks = []
        for item in read_seed("cards.json"):
            card = TaskCard.model_validate(item["card"])
            rating = compute_rating(card).model_dump()
            now = models.utc_now()
            tasks.append(models.Task(
                business_name=item["business_name"], industry=item["industry"],
                draft_text=card.context, card=card.model_dump(), status="published",
                rating=rating, rating_history=[{"total": rating["total"], "at": now}],
                created_at=now, published_at=now,
            ))
        session.add_all([*teams, *tasks])
        session.flush()

        # Proposals depend on both files; missing seed files must not prevent startup.
        if teams and tasks:
            for item in read_seed("proposals.json"):
                task_index, team_index = item["task_index"], item["team_index"]
                if not (0 <= task_index < len(tasks) and 0 <= team_index < len(teams)):
                    raise ValueError("Seed-отклик ссылается на несуществующую задачу или команду")
                task, team = tasks[task_index], teams[team_index]
                proposal = ProposalCreate.model_validate({**item, "team_id": team.id})
                session.add(models.Proposal(
                    task_id=task.id, team_name=team.name, **proposal.model_dump(),
                ))
                task.proposals_count += 1
        update_positions(session)
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
