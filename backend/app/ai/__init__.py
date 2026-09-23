"""AI-слой: модель раскладывает текст пользователя, guard проверяет цитаты, код считает вопросы и баллы.

Сбой любого провайдера не даёт исключения: по цепочке §8 дело доходит до локальной заглушки.
"""
from app.ai import client, guard, prompts, stub
from app.ai.schemas import AnalyzeOut, BuildOut, CardBuild, DraftAnalysis
from app.rating import is_filled
from app.schemas import Answer, Question, TaskCard

__all__ = ["CardBuild", "DraftAnalysis", "analyze_draft", "build_card"]


def analyze_draft(draft_text: str, industry: str) -> DraftAnalysis:
    result = client.complete_json(prompts.analyze_messages(draft_text, industry), AnalyzeOut)
    if result is None:
        return stub.analyze_draft(draft_text, industry)
    out, ai_mode = result
    values, evidence, removed = guard.apply_guard(out.fields, draft_text)
    card = TaskCard(**values)
    return DraftAnalysis(
        card=card, evidence=evidence, removed=removed,
        questions=stub.make_questions(card, out.questions), ai_mode=ai_mode,
    )


def build_card(
    draft_text: str, industry: str, questions: list[Question],
    answers: list[Answer], prev_card: TaskCard,
) -> CardBuild:
    result = client.complete_json(
        prompts.build_messages(draft_text, industry, questions, answers, prev_card), BuildOut,
    )
    if result is None:
        return stub.build_card(draft_text, industry, questions, answers, prev_card)
    out, ai_mode = result
    source = "\n".join([draft_text, *(answer.answer for answer in answers)])
    values, evidence, removed = guard.apply_guard(out.fields, source)
    # Новое значение не прошло guard — остаётся прежнее из prev_card.
    card = TaskCard(**{**prev_card.model_dump(), **values})

    # Ответ, который модель не разложила, не теряем: кладём дословно в поле вопроса, как заглушка.
    field_by_id = {question.id: question.field for question in questions}
    leftovers = [
        answer for answer in answers
        if answer.answer.strip() and field_by_id.get(answer.question_id) not in values
    ]
    if leftovers:
        rest = stub.build_card(draft_text, industry, questions, leftovers, card)
        card, evidence = rest.card, {**rest.evidence, **evidence}
    if not is_filled(card.title):
        card = card.model_copy(update={"title": stub.make_title(draft_text)})
    removed = [item for item in removed if not is_filled(getattr(card, item.field))]
    return CardBuild(card=card, evidence=evidence, removed=removed, ai_mode=ai_mode)
