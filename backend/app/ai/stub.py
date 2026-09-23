"""Локальная заглушка ИИ: AI_MODE=stub и последний шаг fallback.

Ничего не выдумывает: каждое заполненное поле — дословный фрагмент черновика или ответа,
он же уходит в evidence. Вопросы — шаблоны из AGENTS.md §8 по самым весомым пробелам.
"""
import re

from app.ai.schemas import CardBuild, DraftAnalysis
from app.rating import compute_rating, is_filled
from app.schemas import Answer, CardField, Evidence, Question, TaskCard

MAX_FIELD = 2000
MAX_TITLE = 80

TEMPLATES: dict[CardField, tuple[str, str]] = {
    "context": (
        "Что происходит сейчас: какой процесс или проблема, как вы справляетесь с этим сегодня?",
        "Команде нужно понять, как всё устроено сейчас, чтобы не решать не ту задачу.",
    ),
    "need": (
        "Что именно должно измениться после работы команды?",
        "Ясная цель помогает команде понять, что считать решением.",
    ),
    "data": (
        "Какие данные, примеры или материалы вы готовы дать команде (выгрузки, таблицы, доступы)?",
        "С реальными данными команда начнёт работу в первый же день, а не будет их придумывать.",
    ),
    "expected_result": (
        "Какой конкретный результат вы ждёте: прототип, отчёт, модель, сервис?",
        "Команда будет знать, что именно сдавать в конце.",
    ),
    "success_criteria": (
        "По каким измеримым признакам вы поймёте, что решение подходит (цифры, проценты)?",
        "Измеримые критерии помогут принять работу без споров.",
    ),
    "constraints": (
        "Какие есть сроки, требования к технологиям или ограничения по доступу?",
        "Сроки и ограничения помогут командам честно оценить свои силы.",
    ),
    "users": (
        "Кто будет пользоваться решением?",
        "Решение проектируют под конкретных людей и их привычки.",
    ),
    "contact": (
        "Как с вами связаться: email, телефон или Telegram?",
        "Команды смогут задать вопросы напрямую. Можно сразу написать, как удобно созваниваться.",
    ),
    "interaction_format": (
        "Как часто и в каком формате вы готовы консультировать команду?",
        "Команда будет знать, когда ждать обратную связь.",
    ),
}
# При равных баллах сначала то, без чего команде не стартовать; уже заполненные поля — в конце.
PRIORITY: list[CardField] = [
    "data", "expected_result", "success_criteria", "users", "constraints",
    "need", "context", "contact", "interaction_format",
]

NEED_START = r"(?:мы\s+|нам\s+|мне\s+)?(?:хоти|хотел|нужн|надо|необходим|требуется|планиру|задача|цель)"
CONTACT_RE = re.compile(r"\S+@\S+\.\w+|\+?\d[\d\s\-()]{8,}\d|@\w{3,}")
FORMAT_RE = re.compile(
    r"созвон|созвани|встреч|раз в (?:день|неделю|две недели|месяц)|еженедел|ежедневн|zoom|meet|телемост|на связи"
)
# Порядок важен: фрагмент уходит в первое подошедшее поле.
MARKERS: list[tuple[CardField, re.Pattern[str]]] = [
    # CRM, 1С, API сами по себе — не данные («Мы делаем CRM…»), только рядом с «есть / дадим».
    ("data", re.compile(
        r"выгруз|таблиц|csv|xlsx|json|датасет|архив|баз[аеуы]? данных|\bлоги?\b"
        r"|^(?:у нас\s+)?(?:есть|имеется|дадим|передадим|(?:можем|готовы) (?:дать|передать)).*(?:crm|1с|excel|api|данн|отчет)"
    )),
    ("expected_result", re.compile(r"^(?:ждем|ожидаем|результат|на выходе)")),
    ("success_criteria", re.compile(r"^(?:успех|критери)|считать успехом")),
    ("constraints", re.compile(r"срок|дедлайн|бюджет|\bnda\b|стек|не позднее")),
    ("interaction_format", FORMAT_RE),
    ("users", re.compile(
        r"пользоват|для (?:наших |своих )?(?:сотрудник|менеджер|управляющ|продавц|оператор|врач|учител|бухгалтер|курьер)"
    )),
    ("need", re.compile("^" + NEED_START)),
]


def _lower(text: str) -> str:
    return text.lower().replace("ё", "е")


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if part.strip()]


def _clauses(text: str) -> list[str]:
    """Предложения, а «…, хотим …» отделяется в отдельный фрагмент."""
    parts: list[str] = []
    for sentence in _sentences(text):
        parts += re.split(r"[,;]\s+(?=" + NEED_START + ")", sentence, flags=re.IGNORECASE)
    return [part.strip() for part in parts if len(part.strip()) >= 3]


def _as_sentence(text: str) -> str:
    text = text.strip()
    text = text[:1].upper() + text[1:]
    return text if text[-1:] in ".!?…" else text + "."


def _contact_parts(text: str) -> tuple[str, str]:
    """«anna@example.com, созвон раз в неделю» → ("anna@example.com", "созвон раз в неделю")."""
    contacts = [match.group().strip() for match in CONTACT_RE.finditer(text)]
    rest = CONTACT_RE.sub(",", text)
    segments = [segment.strip(" .") for segment in re.split(r"[,;\n]|(?<=[.!?])\s", rest)]
    formats = [segment for segment in segments if len(segment) >= 5 and FORMAT_RE.search(_lower(segment))]
    return ", ".join(contacts), ", ".join(formats)


def extract(text: str) -> tuple[dict[CardField, str], Evidence]:
    """Раскладывает дословные фрагменты текста по полям карточки. Context — весь текст (§8)."""
    context = text.strip()[:MAX_FIELD]
    fields: dict[CardField, str] = {"context": context}
    evidence: Evidence = {"context": context}
    found: dict[CardField, list[str]] = {}
    for clause in _clauses(text):
        if CONTACT_RE.search(clause):
            _, formats = _contact_parts(clause)
            if formats:
                found.setdefault("interaction_format", []).append(formats)
            continue
        lowered = _lower(clause)
        field = next((field for field, pattern in MARKERS if pattern.search(lowered)), None)
        if field:
            found.setdefault(field, []).append(clause)
    for field, clauses in found.items():
        fields[field] = " ".join(_as_sentence(clause) for clause in clauses)[:MAX_FIELD]
        evidence[field] = " ".join(clauses)
    contacts, _ = _contact_parts(text)
    if contacts:
        fields["contact"] = evidence["contact"] = contacts
    return fields, evidence


def question_points(card: TaskCard) -> dict[CardField, int]:
    """Сколько баллов рейтинга принесёт каждое поле — сумма непройденных проверок."""
    points: dict[CardField, int] = {}
    for item in compute_rating(card).missing:
        points[item.field] = points.get(item.field, 0) + item.points
    return points


def make_questions(card: TaskCard, preferred: list | None = None) -> list[Question]:
    """3–5 вопросов: сначала вопросы модели (field, text, why), потом добивка шаблонами по самым весомым пробелам.

    id и points всегда проставляет код. Контакт спрашиваем обязательно, если его нет:
    без него команда не сможет связаться с бизнесом.
    """
    points = question_points(card)
    chosen: dict[CardField, tuple[str, str]] = {}
    for question in preferred or []:
        # Вопрос по уже закрытому полю рейтингу ничего не даст.
        if (question.field in TEMPLATES and points.get(question.field, 0) > 0
                and question.field not in chosen and len(chosen) < 5):
            chosen[question.field] = (question.text, question.why or TEMPLATES[question.field][1])
    ranked = sorted(TEMPLATES, key=lambda field: (
        -points.get(field, 0), is_filled(getattr(card, field)), PRIORITY.index(field),
    ))
    ask_contact = points.get("contact", 0) > 0 and "contact" not in chosen
    if ask_contact and len(chosen) >= 5:
        chosen.pop(list(chosen)[-1])
    target = (3 if chosen else 5) - ask_contact  # вопросы модели только добиваем до минимума
    for field in ranked:
        if len(chosen) >= target:
            break
        if field != "contact" and points.get(field, 0) > 0:
            chosen.setdefault(field, TEMPLATES[field])
    if ask_contact:
        chosen["contact"] = TEMPLATES["contact"]
    for field in ranked:
        if len(chosen) >= 3:
            break
        chosen.setdefault(field, TEMPLATES[field])
    return [
        Question(id=f"q{number}", field=field, text=text, why=why, points=points.get(field, 0))
        for number, (field, (text, why)) in enumerate(chosen.items(), start=1)
    ]


def make_title(draft_text: str) -> str:
    """Предложение с потребностью, иначе первое предложение черновика; не длиннее 80 символов."""
    sentences = _sentences(draft_text) or [draft_text.strip()]
    need = re.compile(r"(?:^|[,;]\s+)" + NEED_START)
    title = next((sentence for sentence in sentences if need.search(_lower(sentence))), sentences[0])
    title = title.rstrip(".!?… ")
    if len(title) > MAX_TITLE:
        title = title[:MAX_TITLE - 1].rsplit(" ", 1)[0].rstrip(",;:—- ") + "…"
    return title


def analyze_draft(draft_text: str, industry: str) -> DraftAnalysis:
    fields, evidence = extract(draft_text)
    card = TaskCard(**fields)
    return DraftAnalysis(card=card, evidence=evidence, questions=make_questions(card), ai_mode="stub")


def build_card(
    draft_text: str, industry: str, questions: list[Question],
    answers: list[Answer], prev_card: TaskCard,
) -> CardBuild:
    fields = prev_card.model_dump()
    draft_fields, draft_evidence = extract(draft_text)
    evidence: Evidence = {}
    answered = {question.field for question in questions
                if any(answer.question_id == question.id and answer.answer.strip() for answer in answers)}

    def put(field: CardField, text: str) -> None:
        # Ответ дополняет то, что уже было в карточке, а не затирает его.
        prev = fields[field].strip()
        if is_filled(prev) and _lower(text) not in _lower(prev):
            fields[field] = f"{_as_sentence(prev)} {_as_sentence(text)}"[:MAX_FIELD]
            quote = draft_evidence.get(field) if prev == draft_fields.get(field) else evidence.get(field)
            evidence[field] = f"{quote} {text}" if quote else text
        else:
            fields[field] = text[:MAX_FIELD]
            evidence[field] = text

    field_by_id = {question.id: question.field for question in questions}
    for answer in answers:
        field, text = field_by_id.get(answer.question_id), answer.answer.strip()
        if field is None or not text:
            continue
        contacts, formats = _contact_parts(text)
        if field == "contact":
            fields["contact"] = ""
            put("contact", contacts or text)
            if contacts and formats and "interaction_format" not in answered and not is_filled(fields["interaction_format"]):
                put("interaction_format", _as_sentence(formats))
                evidence["interaction_format"] = formats
        else:
            put(field, text)
            if contacts and "contact" not in answered and not is_filled(fields["contact"]):
                put("contact", contacts)
    if not is_filled(fields["title"]):
        fields["title"] = make_title(draft_text)
    return CardBuild(card=TaskCard(**fields), evidence=evidence, ai_mode="stub")
