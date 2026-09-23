from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app import ai, rating
from app.db import get_session
from app.models import Task, utc_now
from app.routers.catalog import update_positions
from app.schemas import AnswersSubmit, Question, Rating, TaskCard, TaskCreate
from app.schemas import Task as TaskResponse

router = APIRouter()


def find_task(session: Session, id: int) -> Task:
    task = session.get(Task, id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@router.post("/tasks", response_model=TaskResponse)
def create_task(body: TaskCreate, session: Session = Depends(get_session)):
    analysis = ai.analyze_draft(body.draft_text, body.industry)
    task = Task(
        **body.model_dump(),
        card=analysis.card.model_dump(),
        evidence=analysis.evidence,
        removed=[item.model_dump() for item in analysis.removed],
        questions=[question.model_dump() for question in analysis.questions],
        ai_mode=analysis.ai_mode,
        draft_rating=rating.compute_rating(analysis.card).model_dump(),
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.post("/tasks/{id}/answers", response_model=TaskResponse)
def submit_answers(id: int, body: AnswersSubmit, session: Session = Depends(get_session)):
    task = find_task(session, id)
    if task.status != "clarifying":
        raise HTTPException(status_code=400, detail="Ответы принимаются только на этапе уточнения")
    question_ids = {question["id"] for question in task.questions}
    if any(answer.question_id not in question_ids for answer in body.answers):
        raise HTTPException(status_code=400, detail="Ответ содержит неизвестный вопрос")
    result = ai.build_card(
        task.draft_text,
        task.industry,
        [Question.model_validate(question) for question in task.questions],
        body.answers,
        TaskCard.model_validate(task.card),
    )
    task.answers = [answer.model_dump() for answer in body.answers]
    task.card = result.card.model_dump()
    task.evidence = {**task.evidence, **result.evidence}
    task.removed = [item.model_dump() for item in result.removed]
    task.ai_mode = result.ai_mode
    task.status = "card_ready"
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.post("/rating/preview", response_model=Rating)
def preview_rating(body: TaskCard):
    return rating.compute_rating(body)


@router.put("/tasks/{id}/card", response_model=TaskResponse)
def confirm_card(id: int, body: TaskCard, session: Session = Depends(get_session)):
    task = find_task(session, id)
    if task.status not in {"card_ready", "confirmed", "published"}:
        raise HTTPException(status_code=400, detail="Сначала ответьте на уточняющие вопросы")
    if not 3 <= len(body.title.strip()) <= 120:
        raise HTTPException(status_code=422, detail="Название должно содержать от 3 до 120 символов")
    card = body.model_dump()
    task.evidence = {field: quote for field, quote in task.evidence.items() if card[field] == task.card[field]}
    task.card = card
    task.rating = rating.compute_rating(body).model_dump()
    task.rating_history = [*task.rating_history, {"total": task.rating["total"], "at": utc_now()}]
    if task.status != "published":
        task.status = "confirmed"
    session.add(task)
    update_positions(session)
    session.commit()
    session.refresh(task)
    return task


@router.post("/tasks/{id}/publish", response_model=TaskResponse)
def publish_task(id: int, session: Session = Depends(get_session)):
    task = find_task(session, id)
    if task.status != "confirmed":
        raise HTTPException(status_code=400, detail="Публиковать можно только подтверждённую карточку")
    task.status = "published"
    task.published_at = utc_now()
    session.add(task)
    update_positions(session)
    session.commit()
    session.refresh(task)
    return task


@router.get("/tasks", response_model=list[TaskResponse])
def get_tasks(session: Session = Depends(get_session)):
    return session.exec(select(Task).order_by(Task.id)).all()


@router.get("/tasks/{id}", response_model=TaskResponse)
def get_task(id: int, session: Session = Depends(get_session)):
    return find_task(session, id)
