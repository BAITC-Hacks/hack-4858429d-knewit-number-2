"""Рейтинг готовности задачи 0–100 по AGENTS.md §7. Детерминированно, без LLM."""
import re

from app.schemas import CardField, Level, MissingItem, NextLevel, Rating, RatingCategory, RatingCheck, TaskCard

STOP_LIST = {"нет", "-", "не знаю", "n/a", "tbd", "?"}
DATA_MARKERS = (
    "csv", "xlsx", "json", "pdf",
    "выгруз", "таблиц", "баз", "api", "crm", "1с", "excel", "отчет", "отчёт", "лог", "пример", "датасет",
)
CONSTRAINT_MARKERS = (
    "срок", "недел", "месяц", "дн", "дедлайн", "python", "доступ", "nda", "бюджет", "стек", "технолог",
)
CONTACT_RE = re.compile(r"\S+@\S+\.\S+|\+?\d[\d\s\-()]{8,}|@\w{3,}")
DIGIT_RE = re.compile(r"\d")
NUMBER_RE = re.compile(r"\d|%")

LEVELS: list[tuple[int, Level, str]] = [
    (0, "draft", "Черновик · требует уточнения"),
    (40, "working", "Рабочая"),
    (70, "ready", "Готовая"),
    (90, "priority", "Приоритетная"),
]


def is_filled(text: str) -> bool:
    text = text.strip()
    return len(text) >= 3 and text.lower() not in STOP_LIST


def word_count(text: str) -> int:
    return len(text.split())


def has_marker(text: str, markers: tuple[str, ...]) -> bool:
    text = text.lower()
    return any(marker in text for marker in markers)


def level_for(total: int) -> tuple[Level, str]:
    return next((level, label) for threshold, level, label in reversed(LEVELS) if total >= threshold)


def next_level_for(total: int) -> NextLevel | None:
    for threshold, level, label in LEVELS[1:]:
        if total < threshold:
            return NextLevel(level=level, label=label, threshold=threshold, points_needed=threshold - total)
    return None


def _check(label: str, field: CardField, points: int, passed: bool, hint: str) -> RatingCheck:
    return RatingCheck(
        label=label, field=field, points=points, passed=passed,
        hint=None if passed else f"{hint} (+{points} баллов)",
    )


def _category(key: str, label: str, checks: list[RatingCheck]) -> RatingCategory:
    return RatingCategory(
        key=key, label=label,
        max=sum(check.points for check in checks),
        earned=sum(check.points for check in checks if check.passed),
        checks=checks,
    )


def compute_rating(card: TaskCard) -> Rating:
    filled = {field: is_filled(value) for field, value in card.model_dump().items()}
    context_need = " ".join(getattr(card, field) for field in ("context", "need") if filled[field])

    categories = [
        _category("context_need", "Контекст и потребность", [
            _check("Контекст описан", "context", 5, filled["context"],
                   "Опишите, что происходит сейчас: процесс или проблему"),
            _check("Потребность описана", "need", 5, filled["need"],
                   "Опишите, что должно измениться после работы команды"),
            _check("Контекст и потребность раскрыты подробно (от 25 слов)", "context", 10,
                   word_count(context_need) >= 25,
                   "Раскройте контекст и потребность подробнее: вместе от 25 слов"),
        ]),
        _category("data", "Данные и материалы", [
            _check("Данные указаны", "data", 10, filled["data"],
                   "Укажите, какие данные или материалы получит команда"),
            _check("Данные конкретные: объём, формат или источник", "data", 10,
                   filled["data"] and (bool(DIGIT_RE.search(card.data)) or has_marker(card.data, DATA_MARKERS)),
                   "Уточните данные: объём, формат (CSV, XLSX) или источник (выгрузка, CRM, таблица)"),
        ]),
        _category("expected_result", "Ожидаемый результат", [
            _check("Результат указан", "expected_result", 8, filled["expected_result"],
                   "Укажите, какой результат вы ждёте от команды"),
            _check("Результат описан подробно (от 12 слов)", "expected_result", 7,
                   filled["expected_result"] and word_count(card.expected_result) >= 12,
                   "Опишите результат подробнее: что именно команда передаст, от 12 слов"),
        ]),
        _category("success_criteria", "Критерии успеха", [
            _check("Критерии успеха указаны", "success_criteria", 8, filled["success_criteria"],
                   "Укажите, по каким признакам вы примете решение"),
            _check("Критерий измеримый: число или процент", "success_criteria", 7,
                   filled["success_criteria"] and bool(NUMBER_RE.search(card.success_criteria)),
                   "Добавьте измеримый критерий: число или процент"),
        ]),
        _category("constraints", "Ограничения", [
            _check("Ограничения указаны", "constraints", 5, filled["constraints"],
                   "Укажите сроки, технологии или ограничения по доступу"),
            _check("Ограничения конкретные: срок, стек или доступ", "constraints", 5,
                   filled["constraints"] and (
                       bool(DIGIT_RE.search(card.constraints)) or has_marker(card.constraints, CONSTRAINT_MARKERS)
                   ),
                   "Уточните ограничения: срок в неделях, стек или условия доступа"),
        ]),
        _category("users", "Пользователи", [
            _check("Пользователи указаны", "users", 5, filled["users"],
                   "Укажите, кто будет пользоваться решением"),
            _check("Пользователи описаны подробно (от 5 слов)", "users", 5,
                   filled["users"] and word_count(card.users) >= 5,
                   "Опишите пользователей подробнее: роли и их задачи, от 5 слов"),
        ]),
        _category("business_link", "Связь с бизнесом", [
            _check("Есть контакт: email, телефон или Telegram", "contact", 5,
                   bool(CONTACT_RE.search(card.contact)),
                   "Добавьте контакт: email, телефон или @telegram"),
            _check("Формат взаимодействия указан", "interaction_format", 5, filled["interaction_format"],
                   "Укажите, как часто и в каком формате готовы консультировать команду"),
        ]),
    ]

    total = sum(category.earned for category in categories)
    level, level_label = level_for(total)
    failed = [check for category in categories for check in category.checks if not check.passed]
    missing = [
        MissingItem(field=check.field, hint=check.hint, points=check.points)
        for check in sorted(failed, key=lambda check: -check.points)
    ]
    return Rating(
        total=total, level=level, level_label=level_label,
        categories=categories, missing=missing, next_level=next_level_for(total),
    )
