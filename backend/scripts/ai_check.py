"""Проверка качества ИИ на черновиках из seed/drafts.json с реальным ключом.

    cd backend
    python -m scripts.ai_check            # все 5 черновиков
    python -m scripts.ai_check 1 3        # выбранные id
    python -m scripts.ai_check --json out.json

Для каждого черновика: analyze_draft → ответы из ANSWERS → build_card. Скрипт автоматически
проверяет правила §8 и подсвечивает сомнительные места для ручного просмотра:
- вопросов 3–5, поля не повторяются, у каждого points > 0;
- вопрос опирается на детали черновика (есть общие с черновиком слова);
- у каждого поля от ИИ есть цитата из ввода, цифры в значениях есть во вводе;
- значение не уходит далеко от текста пользователя (доля слов значения, найденных во вводе).
"""
import json
import sys
import time
from pathlib import Path

from app import db  # noqa: F401 — загружает backend/.env
from app.ai import analyze_draft, build_card, guard
from app.rating import compute_rating
from app.schemas import Answer

SEED = Path(__file__).resolve().parents[1] / "seed" / "drafts.json"

# Ответы бизнеса на возможные вопросы по каждому черновику (id → поле → ответ).
ANSWERS: dict[int, dict[str, str]] = {
    1: {
        "data": "Выгрузка чеков из POS за 12 месяцев в CSV",
        "expected_result": "Дашборд продаж по дням и часам для каждой кофейни и три рекомендации, как поднять будни",
        "users": "Управляющие кофейнями и маркетолог сети",
        "contact": "anna@example.com, созвон раз в неделю",
    },
    2: {
        "data": "Журнал электронной очереди за 6 месяцев в Excel: время прихода, время ожидания и услуга",
        "expected_result": "Прогноз загрузки окон по часам и рекомендации, как расставить операторов по сменам",
        "success_criteria": "Среднее ожидание в очереди меньше 20 минут",
        "users": "Руководитель центра и старшие операторы",
        "constraints": "Срок 2 месяца, данные посетителей только обезличенные",
        "contact": "@con_district, встреча раз в две недели",
    },
    3: {
        "expected_result": "Модель, которая помечает заявки для ручной проверки и объясняет причину",
        "success_criteria": "Первичная проверка занимает меньше 5 минут на заявку",
        "users": "Кредитные специалисты отдела рисков",
        "constraints": "Срок 8 недель, Python, данные после подписания NDA",
        "contact": "risk.team@example.com, созвон по пятницам",
    },
    4: {
        "expected_result": "Классификатор тем обращений с API, который подключается к нашему Helpdesk",
        "success_criteria": "Тема определяется правильно не меньше чем в 85% обращений",
        "constraints": "6 недель, Python, выгрузка обезличена",
        "interaction_format": "Созвон раз в неделю и чат в Telegram",
        "contact": "support.lead@example.com",
    },
    5: {
        "users": "Покупатели аптек и провизоры",
        "interaction_format": "Созвон раз в неделю по вторникам",
    },
}


def words(text: str) -> list[str]:
    return guard.normalize(text).split()


def stems(text: str) -> set[str]:
    # Грубая «основа»: первые 5 букв — чтобы «продажи» и «продаж» совпадали.
    return {word[:5] for word in words(text) if len(word) >= 4}


def closeness(value: str, source: str) -> float:
    value_stems = stems(value)
    return len(value_stems & stems(source)) / len(value_stems) if value_stems else 1.0


def check_card(label: str, card, evidence: dict, source: str, problems: list[str], notes: list[str]) -> None:
    for field, value in card.model_dump().items():
        if not value or field == "title":
            continue
        quote = evidence.get(field)
        if not guard.is_supported(quote, source):
            problems.append(f"{label}.{field}: цитата не из текста — «{quote}»")
        if not guard.numbers_supported(value, source):
            problems.append(f"{label}.{field}: цифры не из текста — «{value}»")
        share = closeness(value, source)
        if share < 0.6:
            notes.append(f"{label}.{field}: только {share:.0%} слов из ввода — «{value}»")


def run(draft: dict) -> dict:
    text, industry = draft["text"], draft["industry"]
    problems: list[str] = []
    notes: list[str] = []

    started = time.perf_counter()
    analysis = analyze_draft(text, industry)
    analyze_sec = time.perf_counter() - started

    questions = analysis.questions
    if not 3 <= len(questions) <= 5:
        problems.append(f"вопросов {len(questions)}, нужно 3–5")
    if len({q.field for q in questions}) != len(questions):
        problems.append("поля вопросов повторяются")
    for question in questions:
        if question.points <= 0:
            notes.append(f"{question.id} [{question.field}] даёт 0 баллов")
        if question.field not in {"contact", "interaction_format"} and not stems(question.text) & stems(text):
            notes.append(f"{question.id} [{question.field}] не опирается на детали черновика: «{question.text}»")
    check_card("analyze", analysis.card, analysis.evidence, text, problems, notes)

    replies = ANSWERS.get(draft["id"], {})
    answers = [Answer(question_id=q.id, answer=replies.get(q.field, "")) for q in questions]
    # В полном черновике может не быть вопросов к заготовленным ответам.
    # Не переносим ответ про пользователей, например, в поле данных ради непустоты.
    # Это проверка функций AI-слоя; HTTP-валидация ответов проверяется отдельно.
    started = time.perf_counter()
    result = build_card(text, industry, questions, answers, analysis.card)
    build_sec = time.perf_counter() - started
    source = "\n".join([text, *(answer.answer for answer in answers)])
    check_card("build", result.card, {**analysis.evidence, **result.evidence}, source, problems, notes)

    lost = [
        f"{q.field}: «{a.answer}»" for q, a in zip(questions, answers)
        if a.answer and not getattr(result.card, q.field)
    ]
    problems += [f"ответ потерян — {item}" for item in lost]

    return {
        "id": draft["id"], "industry": industry, "completeness": draft["completeness"], "draft": text,
        "analyze": {
            "ai_mode": analysis.ai_mode, "sec": round(analyze_sec, 1),
            "rating": compute_rating(analysis.card).total,
            "card": {k: v for k, v in analysis.card.model_dump().items() if v},
            "evidence": analysis.evidence, "removed": [r.model_dump() for r in analysis.removed],
            "questions": [q.model_dump() for q in questions],
        },
        "answers": {q.field: a.answer for q, a in zip(questions, answers) if a.answer},
        "build": {
            "ai_mode": result.ai_mode, "sec": round(build_sec, 1),
            "rating": compute_rating(result.card).total,
            "card": {k: v for k, v in result.card.model_dump().items() if v},
            "evidence": result.evidence, "removed": [r.model_dump() for r in result.removed],
        },
        "problems": problems, "notes": notes,
    }


def print_report(report: dict) -> None:
    a, b = report["analyze"], report["build"]
    print(f"\n=== #{report['id']} {report['industry']} ({report['completeness']}) ===")
    print(report["draft"])
    print(f"analyze: {a['ai_mode']}, {a['sec']} с, рейтинг черновика {a['rating']}")
    for field, value in a["card"].items():
        print(f"  {field}: {value}   ← «{a['evidence'].get(field)}»")
    for q in a["questions"]:
        print(f"  {q['id']} [{q['field']} +{q['points']}] {q['text']}")
    print(f"build: {b['ai_mode']}, {b['sec']} с, рейтинг {b['rating']}")
    for field, value in b["card"].items():
        print(f"  {field}: {value}")
    for removed in a["removed"] + b["removed"]:
        print(f"  removed: {removed['field']} — {removed['reason']}")
    for problem in report["problems"]:
        print(f"  ✗ {problem}")
    for note in report["notes"]:
        print(f"  ? {note}")


def main(argv: list[str]) -> int:
    out = None
    if "--json" in argv:
        index = argv.index("--json")
        out = argv[index + 1]
        argv = argv[:index] + argv[index + 2:]
    ids = {int(arg) for arg in argv}
    drafts = [d for d in json.loads(SEED.read_text(encoding="utf-8")) if not ids or d["id"] in ids]
    reports = [run(draft) for draft in drafts]
    for report in reports:
        print_report(report)
    failed = sum(bool(r["problems"]) for r in reports)
    stub = sum(r["analyze"]["ai_mode"] == "stub" or r["build"]["ai_mode"] == "stub" for r in reports)
    print(f"\nИтого: {len(reports)} черновиков, с нарушениями {failed}, с откатом на заглушку {stub}")
    if out:
        Path(out).write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
