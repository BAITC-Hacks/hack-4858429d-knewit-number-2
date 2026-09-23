import re

from app.ai import stub
from app.schemas import Answer, TaskCard

DEMO_DRAFT = "Мы небольшая сеть кофеен в Алматы. Продажи в будние дни падают, хотим понять почему и что делать."
RICH_DRAFT = (
    "Мы онлайн-школа английского. Нужно автоматизировать проверку домашних заданий. "
    "Есть выгрузка из CRM в xlsx за год. Срок — 2 месяца, стек Python. Пишите: ivan@example.com"
)


def words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower().replace("ё", "е")))


def assert_quotes_from(evidence: dict, source: str) -> None:
    for field, quote in evidence.items():
        assert quote and words(quote) <= words(source), f"{field}: «{quote}» нет в тексте пользователя"


def answer_all(analysis, by_field: dict[str, str]) -> list[Answer]:
    return [Answer(question_id=q.id, answer=by_field.get(q.field, "")) for q in analysis.questions]


def test_stub_analyze_demo_draft():
    analysis = stub.analyze_draft(DEMO_DRAFT, "HoReCa")
    assert analysis.ai_mode == "stub"
    assert analysis.card.context == analysis.evidence["context"] == DEMO_DRAFT
    assert analysis.card.need == "Хотим понять почему и что делать."
    assert not analysis.card.data and not analysis.card.users and not analysis.card.title
    assert_quotes_from(analysis.evidence, DEMO_DRAFT)

    questions = analysis.questions
    assert 3 <= len(questions) <= 5
    assert [q.id for q in questions] == [f"q{i}" for i in range(1, len(questions) + 1)]
    assert len({q.field for q in questions}) == len(questions)
    assert questions[0].field == "data" and questions[-1].field == "contact"
    assert all(q.points > 0 and q.text and q.why for q in questions)


def test_stub_analyze_takes_only_quoted_facts():
    analysis = stub.analyze_draft(RICH_DRAFT, "Образование")
    card = analysis.card
    assert card.data == "Есть выгрузка из CRM в xlsx за год."
    assert card.constraints == "Срок — 2 месяца, стек Python."
    assert card.contact == "ivan@example.com"
    assert not card.expected_result and not card.success_criteria and not card.users
    assert_quotes_from(analysis.evidence, RICH_DRAFT)
    asked = {q.field for q in analysis.questions}
    assert 3 <= len(asked) <= 5 and not asked & {"data", "constraints", "contact"}


def test_stub_build_puts_answers_into_their_fields():
    analysis = stub.analyze_draft(DEMO_DRAFT, "HoReCa")
    answers = answer_all(analysis, {
        "data": "  Выгрузка чеков из POS за 12 месяцев в CSV ",
        "users": "Управляющие кофейнями и маркетолог",
        "contact": "anna@example.com, созвон раз в неделю",
    })
    result = stub.build_card(DEMO_DRAFT, "HoReCa", analysis.questions, answers, analysis.card)
    card = result.card
    assert result.ai_mode == "stub"
    assert card.data == result.evidence["data"] == "Выгрузка чеков из POS за 12 месяцев в CSV"
    assert card.users == "Управляющие кофейнями и маркетолог"
    assert card.contact == "anna@example.com"
    assert card.interaction_format == "Созвон раз в неделю."
    assert card.context == DEMO_DRAFT and card.need == analysis.card.need
    assert not card.expected_result and not card.success_criteria
    assert card.title == "Продажи в будние дни падают, хотим понять почему и что делать"
    source = DEMO_DRAFT + " " + " ".join(a.answer for a in answers)
    assert_quotes_from(result.evidence, source)


def test_stub_build_appends_to_filled_field_and_keeps_title():
    analysis = stub.analyze_draft(DEMO_DRAFT, "HoReCa")
    prev = analysis.card.model_copy(update={"title": "Анализ продаж кофеен"})
    need_question = analysis.questions[0].model_copy(update={"field": "need"})
    answers = [Answer(question_id=need_question.id, answer="поднять выручку в будни")]
    result = stub.build_card(DEMO_DRAFT, "HoReCa", [need_question], answers, prev)
    assert result.card.need == "Хотим понять почему и что делать. Поднять выручку в будни."
    assert result.evidence["need"] == "хотим понять почему и что делать. поднять выручку в будни"
    assert result.card.title == "Анализ продаж кофеен"


def test_make_questions_tops_up_model_questions():
    card = TaskCard(context=DEMO_DRAFT)
    model_questions = stub.make_questions(card)[:1]
    questions = stub.make_questions(card, preferred=model_questions)
    assert len(questions) == 3
    assert questions[0].field == model_questions[0].field


def test_long_title_is_cut_by_word():
    title = stub.make_title("Нужно " + "очень " * 30 + "быстро.")
    assert len(title) <= stub.MAX_TITLE and title.endswith("…") and "  " not in title
