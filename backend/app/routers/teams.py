from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app import schemas
from app.db import get_session
from app.models import Team

router = APIRouter()


@router.get("/teams", response_model=list[schemas.Team])
def list_teams(session: Session = Depends(get_session)):
    return session.exec(select(Team).order_by(Team.id)).all()


@router.get("/teams/{id}/recommendations", response_model=list[schemas.Recommendation])
def list_recommendations(id: int, session: Session = Depends(get_session)):
    if session.get(Team, id) is None:
        raise HTTPException(404, "Команда не найдена")
    # ponytail: temporary empty result; replace with recommend() when the engine is ready.
    return []
