import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

from app import models  # Register tables before create_all.

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
engine = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///./app.db"),
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
