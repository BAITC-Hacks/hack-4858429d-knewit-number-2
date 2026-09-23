import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, create_engine, select

from app import models  # Register tables before create_all.
from app.rating import compute_rating
from app.schemas import DraftExample, ProposalCreate, TaskCard

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
engine = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///./app.db"),
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def read_seed(filename: str, *, required: bool = False) -> list[dict]:
    path = SEED_DIR / filename
    try:
        items = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValueError("ожидался JSON-массив объектов")
        if required and not items:
            raise ValueError("seed-файл пуст")
        if filename == "drafts.json":
            items = [DraftExample.model_validate(item).model_dump() for item in items]
        return items
    except (OSError, ValueError) as exc:
        if required:
            raise ValueError(f"Не удалось прочитать seed {path}: {exc}") from exc
        logger.warning("Не удалось прочитать seed %s: %s", path, exc)
        return []


def _populate_seed(session: Session) -> None:
    # Routers import get_session, so reuse catalog ordering after modules are loaded.
    from app.routers.catalog import update_positions

    # Load the complete bundle in one transaction. Partial teams would block retries.
    teams = [models.Team.model_validate(item) for item in read_seed("teams.json", required=True)]
    cards = read_seed("cards.json", required=True)
    proposals = read_seed("proposals.json", required=True)
    read_seed("drafts.json", required=True)
    tasks = []
    for item in cards:
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

    for item in proposals:
        task_index, team_index = item["task_index"], item["team_index"]
        if (type(task_index) is not int or type(team_index) is not int
                or not (0 <= task_index < len(tasks) and 0 <= team_index < len(teams))):
            raise ValueError("proposals.json: отклик ссылается на несуществующую задачу или команду")
        task, team = tasks[task_index], teams[team_index]
        proposal = ProposalCreate.model_validate({**item, "team_id": team.id})
        session.add(models.Proposal(
            task_id=task.id, team_name=team.name, **proposal.model_dump(),
        ))
        task.proposals_count += 1
    update_positions(session)


def seed_database() -> bool:
    try:
        with Session(engine) as session, session.begin():
            # Manually created tasks must not block the demo bundle.
            if session.exec(select(models.Team.id).limit(1)).first() is not None:
                return False
            _populate_seed(session)
        return True
    except Exception as exc:
        # Roll back the entire bundle; keep the API available and allow a later retry.
        logger.warning("Не удалось загрузить seed из %s: %s", SEED_DIR, exc)
        return False


def reset_database() -> None:
    """Replace demo data atomically; callers must obtain explicit confirmation."""
    create_db_and_tables()
    try:
        with Session(engine) as session, session.begin():
            for model in (models.Proposal, models.Task, models.Team):
                session.execute(delete(model))
            _populate_seed(session)
    except Exception as exc:
        logger.warning("Сброс БД отменён, прежние данные сохранены: %s", exc)
        raise


def get_session():
    with Session(engine) as session:
        yield session
