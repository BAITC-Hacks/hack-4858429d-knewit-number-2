import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app import ai, rating
from app.db import get_session
from app.models import Proposal, Task, utc_now
from app.routers.catalog import published_tasks, update_positions
from app.schemas import AnswersSubmit, Question, Rating, TaskCard, TaskCreate
from app.schemas import Task as TaskResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def find_task(session: Session, id: int) -> Task:
    task = session.get(Task, id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


def task_responses(session: Session, tasks: list[Task]) -> list[TaskResponse]:
    if not tasks:
        return []
    positions = {task.id: position for position, task in enumerate(published_tasks(session), start=1)}
    counts = dict(session.exec(
        select(Proposal.task_id, func.count(Proposal.id))
        .where(Proposal.task_id.in_([task.id for task in tasks]))
        .group_by(Proposal.task_id)
    ).all())
    return [
        TaskResponse.model_validate(task).model_copy(update={
            "position": positions.get(task.id), "proposals_count": counts.get(task.id, 0),
        })
        for task in tasks
    ]


@router.post("/tasks", response_model=TaskResponse)
def create_task(body: TaskCreate, session: Session = Depends(get_session)):
    try:
        analysis = ai.DraftAnalysis.model_validate(ai.analyze_draft(body.draft_text, body.industry))
        if not 3 <= len(analysis.questions) <= 5:
            raise ValueError("Ожидалось от 3 до 5 вопросов")
    except Exception as exc:
        logger.warning("Сбой анализа черновика (%s), используется заглушка", type(exc).__name__)
        # ponytail: local fallback until the AI module exposes its own offline entry points.
        context = body.draft_text[:2000]
        analysis = ai.DraftAnalysis(
            card=TaskCard(context=context), evidence={"context": context}, ai_mode="stub",
            questions=[
                Question(id="q1", field="need", points=15,
                         text="Что именно должно измениться после работы команды?",
                         why="Уточните потребность бизнеса и желаемое изменение."),
                Question(id="q2", field="data", points=20,
                         text="Какие данные, примеры или материалы вы готовы дать команде (выгрузки, таблицы, доступы)?",
                         why="Данные и материалы помогут команде начать работу."),
                Question(id="q3", field="expected_result", points=15,
                         text="Какой конкретный результат вы ждёте: прототип, отчёт, модель, сервис?",
                         why="Конкретный результат задаёт цель работы команды."),
            ],
        )
    task = Task(
        **body.model_dump(),
        status="clarifying",
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
    return task_responses(session, [task])[0]


@router.post("/tasks/{id}/answers", response_model=TaskResponse)
def submit_answers(id: int, body: AnswersSubmit, session: Session = Depends(get_session)):
    task = find_task(session, id)
    if task.status != "clarifying":
        raise HTTPException(status_code=400, detail="Ответы принимаются только на этапе уточнения")
    question_ids = {question["id"] for question in task.questions}
    if any(answer.question_id not in question_ids for answer in body.answers):
        raise HTTPException(status_code=400, detail="Ответ содержит неизвестный вопрос")
    try:
        result = ai.CardBuild.model_validate(ai.build_card(
            task.draft_text,
            task.industry,
            [Question.model_validate(question) for question in task.questions],
            body.answers,
            TaskCard.model_validate(task.card),
        ))
    except Exception as exc:
        logger.warning("Сбой сборки карточки (%s), используется заглушка", type(exc).__name__)
        fields, evidence = dict(task.card), {}
        question_fields = {question["id"]: question["field"] for question in task.questions}
        for answer in body.answers:
            if answer.answer.strip():
                field = question_fields[answer.question_id]
                fields[field] = answer.answer
                evidence[field] = answer.answer
        if not fields["title"]:
            fields["title"] = re.split(r"(?<=[.!?])\s+", task.draft_text.strip(), maxsplit=1)[0][:80]
        result = ai.CardBuild(card=TaskCard(**fields), evidence=evidence, ai_mode="stub")
    task.answers = [answer.model_dump() for answer in body.answers]
    task.evidence = {
        field: quote for field, quote in task.evidence.items()
        if getattr(result.card, field) == task.card[field]
    }
    task.evidence = {
        **task.evidence,
        **{field: quote for field, quote in result.evidence.items() if quote and getattr(result.card, field)},
    }
    task.card = result.card.model_dump()
    task.removed = [item.model_dump() for item in result.removed]
    task.ai_mode = result.ai_mode
    task.status = "card_ready"
    session.add(task)
    session.commit()
    session.refresh(task)
    return task_responses(session, [task])[0]


@router.post("/rating/preview", response_model=Rating)
def preview_rating(body: TaskCard):
    return rating.compute_rating(body)


@router.put("/tasks/{id}/card", response_model=TaskResponse)
def confirm_card(id: int, body: TaskCard, session: Session = Depends(get_session)):
    task = find_task(session, id)
    if task.status not in {"card_ready", "confirmed", "published"}:
        raise HTTPException(status_code=400, detail="Сначала ответьте на уточняющие вопросы")
    body.title = body.title.strip()
    if not 3 <= len(body.title) <= 120:
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
    return task_responses(session, [task])[0]


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
    return task_responses(session, [task])[0]


@router.get("/tasks", response_model=list[TaskResponse])
def get_tasks(session: Session = Depends(get_session)):
    return task_responses(session, session.exec(select(Task).order_by(Task.id)).all())


@router.get("/tasks/{id}", response_model=TaskResponse)
def get_task(id: int, session: Session = Depends(get_session)):
    return task_responses(session, [find_task(session, id)])[0]
