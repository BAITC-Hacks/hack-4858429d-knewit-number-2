from typing import Literal

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session, read_seed
from app.models import Task
from app.schemas import CatalogItem, DraftExample, Level

router = APIRouter()

INDUSTRIES = [
    "Ритейл", "HoReCa", "Образование", "Финансы", "Медицина",
    "Логистика", "IT", "Производство", "Госсектор", "Другое",
]


def published_tasks(session: Session) -> list[Task]:
    # ponytail: sort the small demo catalog in memory; use SQL ordering for a large catalog.
    tasks = session.exec(select(Task).where(Task.status == "published")).all()
    return sorted(tasks, key=lambda task: (-(task.rating or {}).get("total", 0), task.published_at, task.id))


def update_positions(session: Session) -> None:
    for position, task in enumerate(published_tasks(session), start=1):
        task.position = position
        session.add(task)


@router.get("/catalog", response_model=list[CatalogItem])
def get_catalog(
    industry: str | None = None,
    level: Level | Literal[""] | None = None,
    session: Session = Depends(get_session),
):
    result = []
    for position, task in enumerate(published_tasks(session), start=1):
        if industry and task.industry != industry:
            continue
        if level and task.rating["level"] != level:
            continue
        result.append(CatalogItem(
            id=task.id,
            title=task.card["title"],
            industry=task.industry,
            business_name=task.business_name,
            need_short=task.card["need"][:140],
            rating_total=task.rating["total"],
            level=task.rating["level"],
            level_label=task.rating["level_label"],
            needs_clarification=task.rating["level"] == "draft",
            position=position,
            proposals_count=task.proposals_count,
            published_at=task.published_at,
        ))
    return result


@router.get("/industries", response_model=list[str])
def get_industries():
    return INDUSTRIES


@router.get("/examples/drafts", response_model=list[DraftExample])
def get_draft_examples():
    return read_seed("drafts.json")
