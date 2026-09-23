from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app import schemas
from app.db import get_session
from app.models import Proposal, Task, Team

router = APIRouter()


@router.post("/tasks/{id}/proposals", response_model=schemas.Proposal)
def create_proposal(
    id: int,
    body: schemas.ProposalCreate,
    session: Session = Depends(get_session),
):
    task = session.get(Task, id)
    if task is None:
        raise HTTPException(404, "Задача не найдена")
    if task.status != "published":
        raise HTTPException(400, "Откликнуться можно только на опубликованную задачу")
    team = session.get(Team, body.team_id)
    if team is None:
        raise HTTPException(404, "Команда не найдена")
    proposal = Proposal(
        task_id=id,
        team_name=team.name,
        **body.model_dump(mode="json"),
    )
    task.proposals_count += 1
    session.add(task)
    session.add(proposal)
    session.commit()
    session.refresh(proposal)
    return proposal


@router.get("/tasks/{id}/proposals", response_model=list[schemas.Proposal])
def list_proposals(id: int, session: Session = Depends(get_session)):
    if session.get(Task, id) is None:
        raise HTTPException(404, "Задача не найдена")
    return session.exec(select(Proposal).where(Proposal.task_id == id).order_by(Proposal.id)).all()


@router.post("/proposals/{id}/decision", response_model=schemas.Proposal)
def decide_proposal(
    id: int,
    body: schemas.ProposalDecision,
    session: Session = Depends(get_session),
):
    proposal = session.get(Proposal, id)
    if proposal is None:
        raise HTTPException(404, "Отклик не найден")
    proposal.status = body.decision
    session.add(proposal)
    session.commit()
    session.refresh(proposal)
    return proposal


@router.post("/proposals/{id}/milestone", response_model=schemas.Proposal)
def confirm_milestone(id: int, session: Session = Depends(get_session)):
    proposal = session.get(Proposal, id)
    if proposal is None:
        raise HTTPException(404, "Отклик не найден")
    if proposal.status != "selected":
        raise HTTPException(400, "Подтвердить этап можно только выбранной команде")
    team = session.get(Team, proposal.team_id)
    if team is None:
        raise HTTPException(404, "Команда не найдена")
    proposal.milestones_confirmed += 1
    team.points += 10
    session.add(proposal)
    session.add(team)
    session.commit()
    session.refresh(proposal)
    return proposal
