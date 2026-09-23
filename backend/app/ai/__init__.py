import re

from pydantic import BaseModel, Field

from app.schemas import AiMode, Answer, Evidence, Question, Removed, TaskCard


class CardBuild(BaseModel):
    card: TaskCard
    evidence: Evidence = Field(default_factory=dict)
    removed: list[Removed] = Field(default_factory=list)
    ai_mode: AiMode = "stub"


class DraftAnalysis(CardBuild):
    questions: list[Question]


def analyze_draft(draft_text: str, industry: str) -> DraftAnalysis:
    # ponytail: только локальная заглушка; провайдеры и guard добавит AI-модуль.
    context = draft_text[:2000]
    return DraftAnalysis(
        card=TaskCard(context=context),
        evidence={"context": context},
        questions=[
            Question(
                id="q1", field="need", points=15,
                text="Что именно должно измениться после работы команды?",
                why="Уточните потребность бизнеса и желаемое изменение.",
            ),
            Question(
                id="q2", field="data", points=20,
                text="Какие данные, примеры или материалы вы готовы дать команде (выгрузки, таблицы, доступы)?",
                why="Данные и материалы помогут команде начать работу.",
            ),
            Question(
                id="q3", field="expected_result", points=15,
                text="Какой конкретный результат вы ждёте: прототип, отчёт, модель, сервис?",
                why="Конкретный результат задаёт цель работы команды.",
            ),
        ],
    )


def build_card(
    draft_text: str, industry: str, questions: list[Question],
    answers: list[Answer], prev_card: TaskCard,
) -> CardBuild:
    fields = prev_card.model_dump()
    evidence: Evidence = {}
    question_fields = {question.id: question.field for question in questions}
    for answer in answers:
        field = question_fields.get(answer.question_id)
        if field is not None and answer.answer.strip():
            fields[field] = answer.answer
            evidence[field] = answer.answer
    if not fields["title"]:
        fields["title"] = re.split(r"(?<=[.!?])\s+", draft_text.strip(), maxsplit=1)[0][:80]
    if fields["context"] and fields["context"] in draft_text:
        evidence.setdefault("context", fields["context"])
    return CardBuild(card=TaskCard(**fields), evidence=evidence)
