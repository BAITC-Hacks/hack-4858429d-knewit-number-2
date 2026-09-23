from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, TypeAdapter, field_validator, model_validator


CardField = Literal[
    "title", "context", "need", "users", "data", "constraints",
    "expected_result", "success_criteria", "contact", "interaction_format",
]
Level = Literal["draft", "working", "ready", "priority"]
TaskStatus = Literal["clarifying", "card_ready", "confirmed", "published"]
AiMode = Literal["openai", "nvidia", "stub"]
ProposalStatus = Literal["pending", "selected", "rejected"]
Evidence = dict[CardField, str | None]
CardText = Annotated[str, Field(max_length=2000)]


class TaskCard(BaseModel):
    title: CardText = ""
    context: CardText = ""
    need: CardText = ""
    users: CardText = ""
    data: CardText = ""
    constraints: CardText = ""
    expected_result: CardText = ""
    success_criteria: CardText = ""
    contact: CardText = ""
    interaction_format: CardText = ""


class Removed(BaseModel):
    field: CardField
    reason: str


class Question(BaseModel):
    id: str
    field: CardField
    text: str
    why: str
    points: int


class Answer(BaseModel):
    question_id: str
    answer: CardText


class RatingCheck(BaseModel):
    label: str
    field: CardField
    points: int
    passed: bool
    hint: str | None


class RatingCategory(BaseModel):
    key: str
    label: str
    max: int
    earned: int
    checks: list[RatingCheck]


class MissingItem(BaseModel):
    field: CardField
    hint: str
    points: int


class NextLevel(BaseModel):
    level: Level
    label: str
    threshold: int
    points_needed: int


class Rating(BaseModel):
    total: int = Field(ge=0, le=100)
    level: Level
    level_label: str
    categories: list[RatingCategory]
    missing: list[MissingItem]
    next_level: NextLevel | None


class RatingHistoryItem(BaseModel):
    total: int
    at: str


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TaskStatus
    business_name: str
    industry: str
    draft_text: str
    questions: list[Question]
    answers: list[Answer]
    card: TaskCard
    evidence: Evidence
    removed: list[Removed]
    draft_rating: Rating | None
    rating: Rating | None
    rating_history: list[RatingHistoryItem]
    position: int | None
    proposals_count: int
    ai_mode: AiMode | None
    created_at: str
    published_at: str | None


class CatalogItem(BaseModel):
    id: int
    title: str
    industry: str
    business_name: str
    need_short: str
    rating_total: int
    level: Level
    level_label: str
    needs_clarification: bool
    position: int
    proposals_count: int
    published_at: str


class Team(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    interests: list[str]
    skills: list[str]
    technologies: list[str]
    points: int


class Proposal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    team_id: int
    team_name: str
    idea: str
    plan: str
    deadline: str
    prototype_url: str
    status: ProposalStatus
    milestones_confirmed: int
    created_at: str


class Recommendation(BaseModel):
    task: CatalogItem
    reasons: list[str]


class DraftExample(BaseModel):
    id: int
    industry: str
    text: str
    completeness: Literal["low", "medium", "high"]


class TaskCreate(BaseModel):
    draft_text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=3000)]
    industry: str
    business_name: str = ""


class AnswersSubmit(BaseModel):
    answers: list[Answer]

    @model_validator(mode="after")
    def require_answer(self) -> Self:
        if not any(answer.answer.strip() for answer in self.answers):
            raise ValueError("Заполните хотя бы один ответ")
        return self


class ProposalCreate(BaseModel):
    team_id: int
    idea: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10)]
    plan: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10)]
    deadline: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    prototype_url: str

    @field_validator("prototype_url")
    @classmethod
    def validate_prototype_url(cls, value: str) -> str:
        value = value.strip()
        TypeAdapter(HttpUrl).validate_python(value)
        return value


class ProposalDecision(BaseModel):
    decision: Literal["selected", "rejected"]
