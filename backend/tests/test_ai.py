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
    assert len(questions) == 5
    assert questions[0].field == model_questions[0].field and questions[-1].field == "contact"


def test_long_title_is_cut_by_word():
    title = stub.make_title("Нужно " + "очень " * 30 + "быстро.")
    assert len(title) <= stub.MAX_TITLE and title.endswith("…") and "  " not in title


def test_stub_reads_full_draft_without_false_data():
    draft = (
        "Мы делаем CRM для салонов красоты. Ждём бота, который отвечает клиентам о записи. "
        "Успехом будет 80% ответов без оператора. Срок 6 недель, доступ к тестовому API после NDA. "
        "Контакт: team@example.com, созвон раз в неделю."
    )
    card = stub.analyze_draft(draft, "IT").card
    assert not card.data
    assert card.expected_result == "Ждём бота, который отвечает клиентам о записи."
    assert card.success_criteria == "Успехом будет 80% ответов без оператора."
    assert card.constraints == "Срок 6 недель, доступ к тестовому API после NDA."
    assert card.contact == "team@example.com"
    assert card.interaction_format == "Созвон раз в неделю."


# --- guard, client и цепочка провайдеров (реальных запросов нет: _chat замокан) ---

import json

import pytest

from app import ai
from app.ai import client, guard
from app.ai.schemas import FieldOut


@pytest.fixture
def providers_env(monkeypatch):
    monkeypatch.setenv("AI_MODE", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("NVIDIA_API_KEY", "test-nvidia")


def fake_chat(monkeypatch, replies: dict[str, list]):
    """replies: провайдер → очередь ответов (строка или исключение). Возвращает журнал вызовов."""
    calls = []

    def chat(provider, messages):
        calls.append(provider.name)
        reply = replies[provider.name].pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(client, "_chat", chat)
    return calls


def analyze_json(**fields) -> str:
    return json.dumps({
        "fields": {name: {"value": value, "evidence": quote} for name, (value, quote) in fields.items()},
        "questions": [
            {"field": "data", "text": "Какие данные о продажах кофеен вы дадите команде?", "why": "Чтобы начать"},
            {"field": "users", "text": "Кто в сети кофеен будет пользоваться решением?", "why": "Под кого делать"},
        ],
    }, ensure_ascii=False)


def test_guard_keeps_real_quote_and_drops_invented():
    fields = {
        "context": FieldOut(value="Продажи в будни падают", evidence="Продажи в будние дни падают"),
        "need": FieldOut(value="Понять причины", evidence="хотим понять, почему и что делать!"),
        "data": FieldOut(value="Выгрузка из 1С за год", evidence="есть выгрузка из 1С за год"),
        "success_criteria": FieldOut(value="Рост продаж на 15%", evidence="Продажи в будние дни падают"),
        "users": FieldOut(value="Бариста", evidence=None),
        "title": FieldOut(value="Падение продаж кофеен в будни", evidence=None),
    }
    values, evidence, removed = guard.apply_guard(fields, DEMO_DRAFT)
    assert values == {
        "title": "Падение продаж кофеен в будни",
        "context": "Продажи в будни падают",
        "need": "Понять причины",
    }
    assert evidence == {"context": "Продажи в будние дни падают", "need": "хотим понять, почему и что делать!"}
    assert {item.field for item in removed} == {"data", "success_criteria", "users"}
    assert all(item.reason == "нет подтверждения в тексте пользователя" for item in removed)


def test_guard_accepts_quote_with_most_words_present():
    source = "Есть выгрузка чеков из кассы за 12 месяцев в формате CSV"
    assert guard.is_supported("выгрузка чеков кассы за 12 месяцев CSV формат", source)
    assert not guard.is_supported("выгрузка заказов из CRM за два года", source)
    assert not guard.is_supported("   ", source)


def test_null_strings_are_empty():
    assert FieldOut.model_validate({"value": "null", "evidence": " None "}) == FieldOut()


def test_providers_chain_from_env(monkeypatch, providers_env):
    assert [p.name for p in client.providers()] == ["openai", "nvidia"]
    monkeypatch.setenv("OPENAI_API_KEY", "")
    assert [p.name for p in client.providers()] == ["nvidia"]
    monkeypatch.setenv("AI_MODE", "stub          # auto | stub")
    assert client.providers() == []


def test_stub_mode_analyze_has_questions(monkeypatch):
    monkeypatch.setenv("AI_MODE", "stub")
    analysis = ai.analyze_draft(DEMO_DRAFT, "HoReCa")
    assert analysis.ai_mode == "stub" and 3 <= len(analysis.questions) <= 5


def test_invalid_json_everywhere_falls_back_to_stub(monkeypatch, providers_env):
    calls = fake_chat(monkeypatch, {"openai": ["не JSON", '{"fields": 1}'], "nvidia": ["```json\n{oops", "[]"]})
    analysis = ai.analyze_draft(DEMO_DRAFT, "HoReCa")
    assert calls == ["openai", "openai", "nvidia", "nvidia"]
    assert analysis.ai_mode == "stub" and 3 <= len(analysis.questions) <= 5


def test_api_error_moves_to_next_provider(monkeypatch, providers_env):
    reply = analyze_json(context=("Продажи в будние дни падают", "Продажи в будние дни падают"))
    calls = fake_chat(monkeypatch, {"openai": [RuntimeError("403 Forbidden")], "nvidia": [f"```json\n{reply}\n```"]})
    analysis = ai.analyze_draft(DEMO_DRAFT, "HoReCa")
    assert calls == ["openai", "nvidia"] and analysis.ai_mode == "nvidia"
    assert analysis.card.context == "Продажи в будние дни падают"


def test_retry_then_guard_and_questions_by_code(monkeypatch, providers_env):
    reply = analyze_json(
        context=("Продажи в будние дни падают", "Продажи в будние дни падают"),
        success_criteria=("Рост выручки на 20%", "хотим вырасти на 20%"),
    )
    calls = fake_chat(monkeypatch, {"openai": ["Вот JSON: {", reply]})
    analysis = ai.analyze_draft(DEMO_DRAFT, "HoReCa")
    assert calls == ["openai", "openai"] and analysis.ai_mode == "openai"
    assert not analysis.card.success_criteria
    assert [item.field for item in analysis.removed] == ["success_criteria"]
    fields = [q.field for q in analysis.questions]
    assert fields[:2] == ["data", "users"] and fields[-1] == "contact"
    assert [q.id for q in analysis.questions] == [f"q{i}" for i in range(1, len(fields) + 1)]
    assert all(q.points > 0 for q in analysis.questions)


def test_build_keeps_answers_model_missed(monkeypatch, providers_env):
    monkeypatch.setenv("AI_MODE", "stub")
    analysis = ai.analyze_draft(DEMO_DRAFT, "HoReCa")
    monkeypatch.setenv("AI_MODE", "auto")
    answers = answer_all(analysis, {
        "data": "Выгрузка чеков из POS за 12 месяцев в CSV",
        "users": "Управляющие кофейнями и маркетолог сети",
    })
    reply = json.dumps({"fields": {
        "title": {"value": "Почему падают продажи кофеен в будни", "evidence": None},
        "data": {"value": "Чеки из POS за 12 месяцев, CSV", "evidence": "Выгрузка чеков из POS за 12 месяцев в CSV"},
        "users": {"value": "Все жители Алматы", "evidence": "жители Алматы любят кофе"},
    }}, ensure_ascii=False)
    fake_chat(monkeypatch, {"openai": [reply]})
    result = ai.build_card(DEMO_DRAFT, "HoReCa", analysis.questions, answers, analysis.card)
    card = result.card
    assert result.ai_mode == "openai"
    assert card.title == "Почему падают продажи кофеен в будни"
    assert card.data == "Чеки из POS за 12 месяцев, CSV"
    assert card.users == result.evidence["users"] == "Управляющие кофейнями и маркетолог сети"
    assert card.context == DEMO_DRAFT and card.need == analysis.card.need
    assert result.removed == []


def test_guard_capitalizes_text_but_not_contact():
    source = "выгрузка чеков за год, пишите anna@example.com"
    values, _, _ = guard.apply_guard({
        "data": FieldOut(value="выгрузка чеков за год", evidence="выгрузка чеков за год"),
        "contact": FieldOut(value="anna@example.com", evidence="anna@example.com"),
    }, source)
    assert values == {"data": "Выгрузка чеков за год", "contact": "anna@example.com"}


@pytest.mark.parametrize("format_value", ["", "Созвон раз в неделю"])
def test_build_recovers_contact_format_without_overwriting_model(monkeypatch, providers_env, format_value):
    analysis = stub.analyze_draft(DEMO_DRAFT, "HoReCa")
    answers = answer_all(analysis, {"contact": "anna@example.com, созвон раз в неделю"})
    fields = {"contact": {"value": "anna@example.com, созвон раз в неделю",
                          "evidence": "anna@example.com, созвон раз в неделю"}}
    if format_value:
        fields["interaction_format"] = {"value": format_value, "evidence": "созвон раз в неделю"}
    fake_chat(monkeypatch, {"openai": [json.dumps({"fields": fields}, ensure_ascii=False)]})
    result = ai.build_card(DEMO_DRAFT, "HoReCa", analysis.questions, answers, analysis.card)
    assert result.ai_mode == "openai"
    assert result.card.interaction_format == (format_value or "Созвон раз в неделю.")
    assert result.evidence["interaction_format"] == "созвон раз в неделю"
    assert result.card.contact == fields["contact"]["value"]


def test_build_does_not_invent_contact_format(monkeypatch, providers_env):
    analysis = stub.analyze_draft(DEMO_DRAFT, "HoReCa")
    answers = answer_all(analysis, {"contact": "anna@example.com"})
    fake_chat(monkeypatch, {"openai": [json.dumps({"fields": {
        "contact": {"value": "anna@example.com", "evidence": "anna@example.com"},
    }})]})
    result = ai.build_card(DEMO_DRAFT, "HoReCa", analysis.questions, answers, analysis.card)
    assert not result.card.interaction_format
    assert "interaction_format" not in result.evidence


def test_quality_check_detects_missing_evidence():
    from scripts.ai_check import check_card

    for evidence in ({}, {"data": None}, {"data": ""}):
        problems, notes = [], []
        check_card("build", TaskCard(data="Выгрузка CSV"), evidence, "Выгрузка CSV", problems, notes)
        assert len(problems) == 1 and "build.data" in problems[0]


def test_quality_check_does_not_move_answer_to_another_field(monkeypatch):
    from scripts import ai_check

    draft = next(item for item in json.loads(ai_check.SEED.read_text(encoding="utf-8")) if item["id"] == 5)
    analysis = stub.analyze_draft(draft["text"], draft["industry"])
    assert not {q.field for q in analysis.questions} & ai_check.ANSWERS[5].keys()
    monkeypatch.setattr(ai_check, "analyze_draft", lambda *args: analysis)
    report = ai_check.run(draft)
    assert report["answers"] == {}
    assert report["build"]["card"]["data"] == analysis.card.data


def test_analyze_recovers_explicit_draft_facts_before_questions(monkeypatch, providers_env):
    draft = (
        "Мы сеть аптек. Нужно узнавать наличие лекарств. "
        "Ждём Telegram-бота с поиском лекарств и адресов аптек. "
        "Успехом будет 80% ответов без провизора. "
        "Контакт: pharma@example.com, созвон раз в неделю."
    )
    reply = json.dumps({"fields": {
        "context": {"value": "Мы сеть аптек.", "evidence": "Мы сеть аптек."},
        "need": {"value": "Узнавать наличие лекарств", "evidence": "Нужно узнавать наличие лекарств."},
    }, "questions": [
        {"field": "success_criteria", "text": "Как измерить успех?", "why": "Для оценки"},
    ]}, ensure_ascii=False)
    fake_chat(monkeypatch, {"openai": [reply]})
    result = ai.analyze_draft(draft, "Ритейл")
    assert result.card.need == "Узнавать наличие лекарств"  # принятое значение не заменено
    assert result.card.expected_result == "Ждём Telegram-бота с поиском лекарств и адресов аптек."
    assert result.card.success_criteria == "Успехом будет 80% ответов без провизора."
    assert result.card.interaction_format == "Созвон раз в неделю."
    assert not any(q.field in {"success_criteria", "interaction_format"} for q in result.questions)
    assert_quotes_from(result.evidence, draft)


def test_complete_card_still_gets_three_questions_marked_optional():
    analysis = stub.analyze_draft(
        "Мы сеть из 25 аптек в Астане. Провизоры тратят до часа в день на однотипные вопросы о наличии лекарств. "
        "Нужно, чтобы покупатели могли сами узнать наличие и цену в ближайшей аптеке. Есть выгрузка остатков из 1С "
        "каждые 15 минут через API и справочник товаров в XLSX. Ждём Telegram-бота, который по названию лекарства "
        "показывает наличие, цену и адреса трёх ближайших аптек. Успехом будет, если бот закрывает 80% вопросов о "
        "наличии без провизора. Срок 6 недель, стек Python, доступ к тестовому API после NDA. Пользоваться будут "
        "покупатели аптек и провизоры. Контакт: pharma.lead@example.com, созвон раз в неделю по вторникам.",
        "Ритейл",
    )
    assert len(analysis.questions) == 3
    assert all(q.points == 0 and q.why == stub.OPTIONAL_WHY for q in analysis.questions)
