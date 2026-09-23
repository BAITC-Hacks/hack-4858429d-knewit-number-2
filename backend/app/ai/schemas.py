from pydantic import BaseModel, Field

from app.schemas import AiMode, Evidence, Question, Removed, TaskCard


class CardBuild(BaseModel):
    card: TaskCard
    evidence: Evidence = Field(default_factory=dict)
    removed: list[Removed] = Field(default_factory=list)
    ai_mode: AiMode = "stub"


class DraftAnalysis(CardBuild):
    questions: list[Question]
