from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.schemas import TaskCard


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: str = "clarifying"
    business_name: str = ""
    industry: str
    draft_text: str
    questions: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    answers: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    card: dict = Field(default_factory=lambda: TaskCard().model_dump(), sa_column=Column(JSON, nullable=False))
    evidence: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    removed: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    draft_rating: dict | None = Field(default=None, sa_column=Column(JSON))
    rating: dict | None = Field(default=None, sa_column=Column(JSON))
    rating_history: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    position: int | None = None
    proposals_count: int = 0
    ai_mode: str | None = None
    created_at: str = Field(default_factory=utc_now)
    published_at: str | None = None


class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    interests: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    technologies: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    points: int = 0


class Proposal(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    team_id: int = Field(foreign_key="team.id")
    team_name: str
    idea: str
    plan: str
    deadline: str
    prototype_url: str
    status: str = "pending"
    milestones_confirmed: int = 0
    created_at: str = Field(default_factory=utc_now)
