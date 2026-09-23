from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app import schemas
from app.db import get_session
from app.models import Task, Team
from app.recommend import recommend
from app.routers.tasks import task_responses

router = APIRouter()


@router.get("/teams", response_model=list[schemas.Team])
def list_teams(session: Session = Depends(get_session)):
    return session.exec(select(Team).order_by(Team.id)).all()


@router.get("/teams/{id}/recommendations", response_model=list[schemas.Recommendation])
def list_recommendations(id: int, session: Session = Depends(get_session)):
    team = session.get(Team, id)
    if team is None:
        raise HTTPException(404, "Команда не найдена")
    # Только подсказка: каталог не фильтруется, место берётся из полного каталога.
    tasks = task_responses(session, session.exec(select(Task).where(Task.status == "published")).all())
    return recommend(schemas.Team.model_validate(team), tasks)
