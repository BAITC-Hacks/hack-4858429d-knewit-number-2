from app.ai import stub
from app.ai.schemas import CardBuild, DraftAnalysis
from app.schemas import Answer, Question, TaskCard

__all__ = ["CardBuild", "DraftAnalysis", "analyze_draft", "build_card"]


def analyze_draft(draft_text: str, industry: str) -> DraftAnalysis:
    # ponytail: пока только локальная заглушка; цепочка OpenAI → NVIDIA → stub придёт в client.py (Z3).
    return stub.analyze_draft(draft_text, industry)


def build_card(
    draft_text: str, industry: str, questions: list[Question],
    answers: list[Answer], prev_card: TaskCard,
) -> CardBuild:
    return stub.build_card(draft_text, industry, questions, answers, prev_card)
