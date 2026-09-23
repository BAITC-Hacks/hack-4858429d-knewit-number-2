from pydantic import BaseModel, Field, field_validator

from app.schemas import AiMode, Evidence, Question, Removed, TaskCard


class CardBuild(BaseModel):
    card: TaskCard
    evidence: Evidence = Field(default_factory=dict)
    removed: list[Removed] = Field(default_factory=list)
    ai_mode: AiMode = "stub"


class DraftAnalysis(CardBuild):
    questions: list[Question]


# Ответ модели (AGENTS.md §8). Строгость здесь минимальная: неизвестные поля и вопросы
# отсеивает код, а факты проверяет guard.

class FieldOut(BaseModel):
    value: str | None = None
    evidence: str | None = None

    @field_validator("value", "evidence", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        # Модели иногда пишут "null" строкой или отдают числа.
        if value is None:
            return None
        value = str(value).strip()
        return None if value.lower() in {"", "null", "none"} else value


class QuestionOut(BaseModel):
    field: str
    text: str = Field(min_length=5)
    why: str = ""


class BuildOut(BaseModel):
    fields: dict[str, FieldOut]


class AnalyzeOut(BuildOut):
    questions: list[QuestionOut]
