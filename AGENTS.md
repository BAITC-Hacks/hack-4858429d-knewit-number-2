# AGENTS.md — TaskReady

Инструкции для AI-агентов (Codex и др.) и людей в команде. Читать перед любой задачей.
Хакатон HackAlem AI, кейс AI Sana «Рейтинг качества бизнес-задач и открытый выбор команд», 5 часов.

## 1. Что строим

Веб-приложение: представитель бизнеса превращает сырое описание задачи в полноценную карточку, получает рейтинг готовности 0–100 и публикует задачу в открытом каталоге. Студенческие команды откликаются, бизнес вручную выбирает.

Сквозной сценарий (всё работает в UI, не на слайдах):
1. Черновик — бизнес вводит краткое описание и отрасль.
2. Уточнение — ИИ находит недостающие сведения и задаёт 3–5 вопросов.
3. Карточка — ИИ собирает редактируемую карточку только из слов пользователя, бизнес правит и подтверждает.
4. Рейтинг — код считает баллы по формуле (§7), показывает разбивку и что добавить.
5. Каталог — задача публикуется на месте по рейтингу.
6. Команда смотрит каталог и отправляет отклик.
7. Бизнес сравнивает отклики и сам выбирает одну, несколько или ни одной команды.
8. (stretch) Бизнес подтверждает этап — выбранная команда получает баллы.

## 2. Жёсткие правила кейса — не нарушать

- ИИ не добавляет фактов, которых не сообщал пользователь. У каждого поля, заполненного ИИ, есть цитата-источник (evidence) из ввода. Нет подтверждения — поле пустое.
- Карточка публикуется только после ручного подтверждения человеком.
- Рейтинг считает код (не LLM) и только по подтверждённой карточке. Живой прогноз в редакторе подписан как прогноз.
- Рейтинг пересчитывается после каждого подтверждения и определяет позицию в каталоге.
- Низкий рейтинг не скрывает задачу и не запрещает отклик.
- Рекомендации командам — только задачи с рейтингом ≥ 40, и они никогда не фильтруют каталог.
- Никакого автоматического выбора или назначения команд. Выбрать или отклонить — только ручное действие бизнеса.
- Персональные и чувствительные признаки участников не используются.
- Не делаем: регистрацию и авторизацию (роль — переключатель в шапке), чат, уведомления, файлы, мобильную вёрстку, векторные БД, обучение моделей.
- Секреты только в `.env`. Ключи никогда не коммитим.

## 3. Стек

- Backend: Python 3.11+, FastAPI, SQLModel + SQLite, Pydantic v2, openai SDK, pytest.
- Frontend: React + Vite + TypeScript, Ant Design 5 (локаль ru_RU), react-router-dom.
- LLM: OpenAI (structured output) → NVIDIA Build (OpenAI-совместимый API) → локальная заглушка.
- Интерфейс на русском. Код, имена полей и API — на английском.

## 4. Структура и владельцы

```
AGENTS.md, TASKS.md, README.md, .gitignore   ← лид
backend/
  requirements.txt, .env.example             ← лид
  app/
    main.py, db.py, models.py                ← лид
    schemas.py                               ← лид. КОНТРАКТ API, менять только через лида
    routers/  tasks.py catalog.py proposals.py teams.py   ← лид
    rating.py                                ← Зарип (движок рейтинга)
    recommend.py                             ← Зарип (stretch)
    ai/  __init__.py client.py prompts.py guard.py stub.py schemas.py   ← Зарип
  seed/  drafts.json cards.json teams.json proposals.json              ← Зарип
  tests/                                     ← каждый пишет тесты своего модуля
frontend/                                    ← Аслан
docs/                                        ← Зарип (примеры ИИ и сценарий демо)
```

Агент меняет файлы только в зоне своей задачи. Нужна правка чужой зоны или контракта — остановись и напиши, что именно поменять.

## 5. Запуск

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # ключи необязательны: без них работает режим заглушки
uvicorn app.main:app --reload --port 8000           # http://localhost:8000/docs
pytest

# frontend
cd frontend
npm install
npm run dev                       # http://localhost:5173, /api проксируется на :8000
```

`backend/.env.example`:
```
OPENAI_API_KEY=
OPENAI_MODEL=
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=
AI_MODE=auto          # auto | stub
DATABASE_URL=sqlite:///./app.db
```

## 6. Контракт API

Источник правды — `backend/app/schemas.py`. Фронт зеркалит его в `frontend/src/api/types.ts`. Имена полей и значения enum не менять без лида.

```ts
type CardField = "title" | "context" | "need" | "users" | "data" | "constraints"
  | "expected_result" | "success_criteria" | "contact" | "interaction_format";

interface TaskCard {            // все поля — строки, "" = не заполнено
  title: string;                // Название
  context: string;              // Контекст: что происходит сейчас
  need: string;                 // Потребность: что нужно изменить
  users: string;                // Для кого решение
  data: string;                 // Доступные данные, примеры, источники
  constraints: string;          // Сроки, технологии, доступы, иные границы
  expected_result: string;      // Конкретный результат работы команды
  success_criteria: string;     // Измеримые признаки принятия решения
  contact: string;              // Email, телефон или @telegram
  interaction_format: string;   // Формат консультаций и обратной связи
}
type Evidence = Partial<Record<CardField, string | null>>;   // цитата из ввода для полей от ИИ
interface Removed { field: CardField; reason: string }        // что ИИ не стал заполнять и почему

interface Question { id: string; field: CardField; text: string; why: string; points: number }
interface Answer { question_id: string; answer: string }

type Level = "draft" | "working" | "ready" | "priority";
interface RatingCheck { label: string; field: CardField; points: number; passed: boolean; hint: string | null }
interface RatingCategory { key: string; label: string; max: number; earned: number; checks: RatingCheck[] }
interface MissingItem { field: CardField; hint: string; points: number }
interface Rating {
  total: number;                  // 0..100
  level: Level; level_label: string;
  categories: RatingCategory[];   // 7 категорий в порядке §7
  missing: MissingItem[];         // непройденные проверки по убыванию points
  next_level: { level: Level; label: string; threshold: number; points_needed: number } | null;
}

type TaskStatus = "clarifying" | "card_ready" | "confirmed" | "published";
type AiMode = "openai" | "nvidia" | "stub";

interface Task {
  id: number; status: TaskStatus; business_name: string; industry: string;
  draft_text: string; questions: Question[]; answers: Answer[];
  card: TaskCard; evidence: Evidence; removed: Removed[];
  draft_rating: Rating | null;    // оценка черновика (прогноз)
  rating: Rating | null;          // рейтинг ПОДТВЕРЖДЁННОЙ карточки
  rating_history: { total: number; at: string }[];
  position: number | null;        // место в каталоге, если опубликована
  proposals_count: number; ai_mode: AiMode | null;
  created_at: string; published_at: string | null;
}

interface CatalogItem {
  id: number; title: string; industry: string; business_name: string; need_short: string;
  rating_total: number; level: Level; level_label: string;
  needs_clarification: boolean;   // level === "draft"
  position: number; proposals_count: number; published_at: string;
}

interface Team { id: number; name: string; interests: string[]; skills: string[]; technologies: string[]; points: number }

type ProposalStatus = "pending" | "selected" | "rejected";
interface Proposal {
  id: number; task_id: number; team_id: number; team_name: string;
  idea: string; plan: string; deadline: string; prototype_url: string;
  status: ProposalStatus; milestones_confirmed: number; created_at: string;
}

interface Recommendation { task: CatalogItem; reasons: string[] }
interface DraftExample { id: number; industry: string; text: string; completeness: "low" | "medium" | "high" }
```

| Метод и путь | Тело → ответ | Правила |
|---|---|---|
| `POST /api/tasks` | `{draft_text, industry, business_name?}` → Task | status=clarifying. ИИ извлекает уже известное, код считает draft_rating, 3–5 вопросов |
| `POST /api/tasks/{id}/answers` | `{answers: Answer[]}` → Task | status=card_ready. ИИ собирает card + evidence, rating ещё null |
| `POST /api/rating/preview` | TaskCard → Rating | живой прогноз для редактора, ничего не сохраняет |
| `PUT /api/tasks/{id}/card` | TaskCard → Task | ручное подтверждение: сохранить, посчитать rating, дописать rating_history, пересчитать position. Если была published — остаётся published |
| `POST /api/tasks/{id}/publish` | — → Task | только из confirmed; рейтинг публикацию не блокирует |
| `GET /api/tasks` | → Task[] | все задачи, для «Мои задачи» |
| `GET /api/tasks/{id}` | → Task | |
| `GET /api/catalog?industry=&level=` | → CatalogItem[] | только published, по убыванию рейтинга |
| `GET /api/industries` | → string[] | |
| `GET /api/examples/drafts` | → DraftExample[] | 5 черновиков из seed |
| `GET /api/teams` | → Team[] | |
| `GET /api/teams/{id}/recommendations` | → Recommendation[] | stretch, §9 |
| `POST /api/tasks/{id}/proposals` | `{team_id, idea, plan, deadline, prototype_url}` → Proposal | только для published, любой рейтинг, число не ограничено |
| `GET /api/tasks/{id}/proposals` | → Proposal[] | |
| `POST /api/proposals/{id}/decision` | `{decision: "selected" \| "rejected"}` → Proposal | только ручное действие, можно выбрать несколько |
| `POST /api/proposals/{id}/milestone` | — → Proposal | stretch: только selected; milestones_confirmed += 1, команде +10 points |

- Ошибки: 400/404/422 с `{"detail": "понятный текст на русском"}`. Сбой ИИ никогда не даёт 500: срабатывает fallback, в ответе `ai_mode`.
- Валидация: draft_text 20–3000 символов; поля карточки ≤ 2000; title при подтверждении 3–120; ответы можно оставлять пустыми, но хотя бы один непустой; idea и plan ≥ 10 символов; deadline не пустой; prototype_url — http(s) URL.
- Статусы: clarifying → card_ready → confirmed → published.
- Позиция: место среди published по rating.total desc, при равенстве выше раньше опубликованная. Всегда по полному каталогу, фильтры её не меняют.

## 7. Формула рейтинга (`backend/app/rating.py`, детерминированно, без LLM)

`compute_rating(card: TaskCard) -> Rating`. Веса из кейса. Каждая категория = «поле заполнено» + «поле конкретное».

| Категория (key) | Вес | Проверка → баллы |
|---|---|---|
| Контекст и потребность (`context_need`) | 20 | context заполнен → 5; need заполнен → 5; context + need вместе ≥ 25 слов → 10 |
| Данные и материалы (`data`) | 20 | data заполнено → 10; есть конкретика: цифра, формат (csv, xlsx, json, pdf) или маркер (выгруз, таблиц, баз, api, crm, 1с, excel, отчет, отчёт, лог, пример, датасет) → 10 |
| Ожидаемый результат (`expected_result`) | 15 | заполнено → 8; ≥ 12 слов → 7 |
| Критерии успеха (`success_criteria`) | 15 | заполнено → 8; есть число или % → 7 |
| Ограничения (`constraints`) | 10 | заполнено → 5; есть цифра или маркер (срок, недел, месяц, дн, дедлайн, python, доступ, nda, бюджет, стек, технолог) → 5 |
| Пользователи (`users`) | 10 | заполнено → 5; ≥ 5 слов → 5 |
| Связь с бизнесом (`business_link`) | 10 | contact похож на email, телефон или @username → 5; interaction_format заполнен → 5 |

- «Заполнено»: после strip ≥ 3 символов и не из стоп-листа («нет», «-», «не знаю», «n/a», «tbd», «?»).
- Маркеры ищутся подстрокой в lower-case. Слово — токен по пробелам.
- Контакт: email `\S+@\S+\.\S+`, телефон `\+?\d[\d\s\-()]{8,}`, telegram `@\w{3,}`.
- У каждой проверки: label, field, points, passed и hint для непройденной («Добавьте измеримый критерий: число или процент (+7)»).
- Уровни: 0–39 `draft` «Черновик · требует уточнения», 40–69 `working` «Рабочая», 70–89 `ready` «Готовая», 90–100 `priority` «Приоритетная».
- `next_level` — ближайший порог выше total (40/70/90) и сколько не хватает. При total ≥ 90 — null.
- title не оценивается, но обязателен для подтверждения.

## 8. AI-слой (`backend/app/ai/`)

Сигнатуры не менять:
```python
def analyze_draft(draft_text: str, industry: str) -> DraftAnalysis: ...
    # DraftAnalysis: card: TaskCard, evidence: dict, removed: list, questions: list[Question], ai_mode: str
def build_card(draft_text: str, industry: str, questions: list[Question],
               answers: list[Answer], prev_card: TaskCard) -> CardBuild: ...
    # CardBuild: card: TaskCard, evidence: dict, removed: list, ai_mode: str
```

Выход модели. Для analyze:
```json
{"fields": {"context": {"value": "...", "evidence": "дословная цитата"},
            "data": {"value": null, "evidence": null}},
 "questions": [{"field": "data", "text": "...", "why": "..."}]}
```
Для build — `{"fields": {...}}` в том же формате. Источник цитат — черновик и ответы.

- Промпты в `prompts.py`: только факты пользователя; evidence — дословная цитата, иначе value = null; вопросы конкретные, с опорой на детали черновика, по самым весомым пустым полям; ответ только JSON; язык русский.
- `guard.py`: normalize = lower, ё→е, без пунктуации, схлопнуть пробелы. Поле принимается, если evidence непустое И (normalize(evidence) — подстрока источника ИЛИ ≥ 70% слов evidence длиной ≥ 4 есть в источнике). Иначе value = "" и в removed: `{"field": ..., "reason": "нет подтверждения в тексте пользователя"}`. title может быть кратким пересказом без evidence, ≤ 100 символов.
- Вопросов всегда 3–5. Модель дала меньше — добить шаблонами по `missing` из compute_rating. `id` ("q1"…) и `points` (сумма баллов непройденных проверок этого поля) проставляет код, не модель.
- build_card: значение из prev_card остаётся, если новое не прошло guard.
- `client.py`: AI_MODE=stub → сразу заглушка. Иначе OpenAI (если есть ключ) → NVIDIA (если есть ключ) → заглушка. На каждом провайдере: ответ → json.loads → Pydantic-валидация → при ошибке один повтор с напоминанием о схеме → следующий провайдер. Таймаут 20 с. Ошибки — logging.warning. `ai_mode` = кто реально ответил.
- `stub.py`: analyze — context = черновик (evidence = черновик), вопросы по шаблонам; build — ответ идёт в поле своего вопроса (evidence = ответ), title = первое предложение черновика ≤ 80 символов.

Шаблоны вопросов (для stub и добивки):
- context: «Что происходит сейчас: какой процесс или проблема, как вы справляетесь с этим сегодня?»
- need: «Что именно должно измениться после работы команды?»
- data: «Какие данные, примеры или материалы вы готовы дать команде (выгрузки, таблицы, доступы)?»
- expected_result: «Какой конкретный результат вы ждёте: прототип, отчёт, модель, сервис?»
- success_criteria: «По каким измеримым признакам вы поймёте, что решение подходит (цифры, проценты)?»
- constraints: «Какие есть сроки, требования к технологиям или ограничения по доступу?»
- users: «Кто будет пользоваться решением?»
- contact: «Как с вами связаться: email, телефон или Telegram?»
- interaction_format: «Как часто и в каком формате вы готовы консультировать команду?»

## 9. Рекомендации (stretch, `backend/app/recommend.py`)

`recommend(team: Team, tasks: list[Task]) -> list[Recommendation]`. Токены команды — слова из interests, skills, technologies (lower). Текст задачи — отрасль и все поля карточки (lower). score = число токенов команды, найденных в тексте задачи (по основе ≥ 4 символов). Только published с rating ≥ 40. Сортировка: score desc, потом rating desc. Топ-3 со score > 0. reasons — совпавшие слова: «совпадает: python, аналитика». Каталог не фильтруется.

## 10. Seed-данные (`backend/seed/`)

Грузятся на старте, если БД пустая. Всё на русском, компании и люди вымышленные, контакты вида name@example.com.
- `drafts.json` — 5 черновиков `{id, industry, text, completeness: low|medium|high}` разной полноты (кнопка «Взять пример»).
- `cards.json` — 5 опубликованных задач `{business_name, industry, card: TaskCard, expected_score}` с баллами ≈ 94, 81, 66, 48, 25, чтобы в каталоге были все 4 уровня. Рейтинг при загрузке считает compute_rating, тест сверяет с expected_score.
- `teams.json` — 5 команд `{name, interests[], skills[], technologies[]}`, одна из них — DataCats (для демо).
- `proposals.json` — 5 откликов `{task_index, team_index, idea, plan, deadline, prototype_url}` на seed-задачи.

Отрасли: Ритейл, HoReCa, Образование, Финансы, Медицина, Логистика, IT, Производство, Госсектор, Другое.

## 11. Демо-сценарий (golden path, до 5 минут)

1. Роль «Бизнес» → /tasks/new. Черновик: «Мы небольшая сеть кофеен в Алматы. Продажи в будние дни падают, хотим понять почему и что делать.» Отрасль HoReCa → оценка черновика ≈ 10, 3–5 вопросов с «+N баллов».
2. Отвечаем про данные (выгрузка чеков из POS за 12 месяцев в CSV), результат (дашборд продаж по дням и часам и 3 рекомендации), пользователей (управляющие кофейнями и маркетолог), контакт и формат (email, созвон раз в неделю). Критерии успеха и ограничения пока пропускаем.
3. Карточка с цитатами-источниками → «Подтвердить» → ≈ 65 «Рабочая» → «Опубликовать» → место #4.
4. «Что повысит рейтинг» → добавляем критерий «рост выручки в будни на 15% за 2 месяца» и ограничения «срок 6 недель, Python, доступ к данным после NDA» → «Подтвердить» → ≈ 90 «Приоритетная», место #4 → #2.
5. Роль «Команда» (DataCats) → каталог → задача → «Откликнуться»: идея, план, срок, ссылка на прототип.
6. Роль «Бизнес» → задача → отклики → «Выбрать» DataCats, «Отклонить» другой отклик.
7. (stretch) «Подтвердить этап» → DataCats получает +10 баллов.

Точные цифры подгоняем под seed в конце. Свою часть проверяйте на этом сценарии.

## 12. Git и Definition of Done

- Перед каждой задачей `git pull --rebase`. Маленькие коммиты, мерж в main каждые 30–45 минут, main всегда запускается.
- Каждый коммитит со своего GitHub-аккаунта.
- Дифф агента читаем перед мержем. После 17:30 — только исправления багов.
- Готово = работает в UI на демо-сценарии, нет ошибок в консоли и 500 в API, тесты модуля проходят, закоммичено в main.
