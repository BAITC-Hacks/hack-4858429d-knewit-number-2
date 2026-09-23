# NVIDIA: восстановление доступа и вариант запуска через Brev

Проверено 23 сентября 2026 года. Документ не содержит ключей доступа.

## Рабочее подключение через Brev

Модель `nvidia/NVIDIA-Nemotron-Nano-9B-v2` отвечает через SSH-туннель:
Windows `127.0.0.1:9000` → Brev `127.0.0.1:8000`.
Прямой SSH доступен на `64.247.196.218:22`, пользователь `shadeform`.
Отпечаток сервера сверён с выводом в Jupyter:
`SHA256:VYsTFesqvSoDIo3f64IklhgycFMsJYj8YDAHJmD+hh8`.

На компьютере Зарипа ключ расположен в `%USERPROFILE%\.ssh\taskready_brev_ed25519`,
проверенный публичный ключ сервера — в `taskready_brev_known_hosts` в той же папке.
Эти файлы не находятся в репозитории. На другом компьютере потребуется собственная
настройка SSH; при пересоздании машины нужно заново проверить адрес и отпечаток.

### Повторный запуск после перезагрузки Windows

Из корня проекта, в первом окне PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docs\start_nvidia_tunnel.ps1
```

Оставить окно открытым. Во втором окне PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docs\start_backend_nvidia.ps1
```

Backend будет доступен на <http://127.0.0.1:8000/docs>.
`ExecutionPolicy Bypass` относится только к запускаемому процессу PowerShell.
Если порт занят, сначала проверить уже работающий процесс; повторный запуск не нужен.

Скрипт backend выбирает NVIDIA через переменные процесса. Это нужно, поскольку
обычный запуск при заполненном `OPENAI_API_KEY` сначала вызывает OpenAI.
Сохранённые ключи в `.env` скрипт не меняет. Для собственного сервера используется
значение `NVIDIA_API_KEY=local-brev`: это непустая заглушка для SDK, а доступ защищён SSH.
Ключ NVIDIA NGC для обращения к этому серверу не нужен.

### Что проверено с компьютера

- SSH-вход по ключу, соответствие отпечатка и `GET /v1/models`: успешно.
- Скрипт повторного запуска туннеля проверен на временном порту 9001;
  проверочный процесс закрыт, основной туннель использует 9000.
- Реальные функции `analyze_draft` и `build_card`: `ai_mode=nvidia`,
  10.998 и 10.675 секунды соответственно.
- Флоу API на отдельной временной SQLite-базе: создание задачи — HTTP 200,
  5 вопросов, 11.212 с; ответы и карточка — HTTP 200, 10.397 с,
  все возвращённые evidence являются дословными подстроками ввода.
- Публикация до подтверждения — ожидаемый HTTP 400; подтверждение — HTTP 200,
  рейтинг 75; публикация после подтверждения — HTTP 200, позиция 3 в тестовом каталоге.
- Эти числа относятся к проверочному набору ответов, а не к сценарию демо Z6.
- Локальный backend перезапущен через `start_backend_nvidia.ps1`, `/openapi.json`
  вернул HTTP 200. Проверка UI в эту проверку не входила.

**Ограничение Z0:** эта конфигурация Nemotron пока не выполнила требование ответа
быстрее 5 секунд с качественным результатом. Короткие промпты давали 3–6 секунд,
но ухудшали цитаты и вопросы; в приложение они не перенесены. Обычный промпт
отрабатывает примерно за 10–11 секунд. Ускоренные варианты и полный отчёт сохранены
вне репозитория, в `%TEMP%\taskready-z0\nvidia-brev-*.json`.

Машина Brev продолжает расходовать средства по тарифу $1.06/час.
Завершение SSH или backend не прекращает аренду. После завершения работы
нужно сохранить нужные данные и удалить окружение в Brev.

## Что установлено

- Запрос списка моделей к `https://integrate.api.nvidia.com/v1/models` возвращал HTTP 200.
- Генерация через `/v1/chat/completions` неоднократно возвращала
  `403 — Authorization failed` для двух моделей:
  `nv-mistralai/mistral-nemo-12b-instruct` и `mistralai/mistral-7b-instruct-v0.3`.
- В карточке одного из использованных ключей на скриншоте был только `NGC Catalog`.
- В форме создания ключа организации `sunrise` были доступны только
  `Secrets Manager` и `NGC Catalog`; `Public API Endpoints` отсутствовал.
- После замены ключа запрос генерации также вернул 403.
- Скриншота прав самого последнего ключа нет. Его права не считаем установленными.
- Пользователь сообщил о проблеме доступа к Build из Казахстана.
  По HTTP 403 нельзя установить географическую причину: подтверждения общего
  запрета сервиса для Казахстана мы не получили.

Повторять создание ключей с теми же правами бессмысленно для диагностики.
Следующий шаг — решить вопрос с правами аккаунта либо подготовить собственный сервер модели.

## Путь 1. Обращение в NVIDIA Build

NVIDIA указывает адрес **help@build.nvidia.com** для проблем проверки аккаунта.
Нужно приложить адрес регистрации, номера телефонов, которые пытались проверить,
и описание ошибки со скриншотом. Это обращение в поддержку; успешная активация
и срок ответа не гарантированы.

Источники:

- [Resolving Account Access issues — закреплённая инструкция NVIDIA](https://forums.developer.nvidia.com/t/resolving-account-access-issues/345920)
- [Account Access & Verification Update](https://forums.developer.nvidia.com/t/account-access-verification-update/360900)
- [NGC: назначение сервисов ключу](https://docs.nvidia.com/ngc/latest/ngc-user-guide.html#assigning-services-to-your-personal-api-key)

### Готовый текст письма

Перед отправкой заполни поля в квадратных скобках. Если телефон не пытался
подтверждать, так и напиши. Укажи только реально наблюдаемую ошибку на Build.
Сам ключ и содержимое `.env` в письмо не включай.

**To:** help@build.nvidia.com

**Subject:** NVIDIA Build access issue — Kazakhstan, missing Public API Endpoints, HTTP 403

```text
Hello NVIDIA Build Support,

I am developing TaskReady for the HackAlem AI hackathon and need access to
NVIDIA-hosted inference APIs.

Registered email: [my NVIDIA account email]
Country: Kazakhstan
NGC organization shown in the console: sunrise
Phone number(s) attempted for verification: [number(s), or "not attempted"]
Build verification error: [exact message or description; screenshot attached]

Observed API behavior:
- GET https://integrate.api.nvidia.com/v1/models returned HTTP 200.
- POST https://integrate.api.nvidia.com/v1/chat/completions returned:
  {"status":403,"title":"Forbidden","detail":"Authorization failed"}
- Tested model IDs:
  nv-mistralai/mistral-nemo-12b-instruct
  mistralai/mistral-7b-instruct-v0.3

In the NGC key creation dialog, Services Included only offers Secrets Manager
and NGC Catalog. Public API Endpoints is missing. A replacement key did not
resolve the inference error.

Please check my account verification and organization permissions, confirm
whether hosted API access is available for my account, and advise what is
needed to enable Public API Endpoints.

I can provide additional account information through a secure support channel.
No API secrets are included in this message.

Thank you,
Zarip
```

Прикрепи скриншот доступных Services Included и фактической ошибки на Build.
Текст подготовлен локально; письмо не отправлено.

После подтверждения доступа со стороны NVIDIA создаём ключ с нужным сервисом
и выполняем один запрос генерации. Если он успешен — повторяем Z0 на три запуска.

## Путь 2. Модель NVIDIA через vLLM на GPU в Brev

Это вариант развёртывания, предложенный для решения проблемы доступа.
В исходном AGENTS.md указан NVIDIA Build; собственный сервер меняет место запуска
модели. Если условия мероприятия требуют именно hosted Build, допустимость
замены нужно уточнить у лида/организаторов.

Первоначально рассматривали NVIDIA NIM. Проверка списка тегов репозитория
`nim/nv-mistralai/mistral-nemo-12b-instruct` в `nvcr.io` вернула HTTP 401,
в том числе после получения registry bearer token с текущим ключом.
Образ не скачан: доступ к этому варианту развёртывания не подтверждён.

Пользователь запустил открытую модель `nvidia/NVIDIA-Nemotron-Nano-9B-v2`
из официального репозитория NVIDIA на Hugging Face через vLLM в Brev.
Это собственный сервер с OpenAI-совместимым API. Развёртывание через vLLM
не следует обозначать как NVIDIA NIM или hosted Build.

Проверено без ключа Hugging Face:

- API метаданных вернул HTTP 200 и `gated: false`.
- HEAD первого файла весов в ревизии
  `6533e8de2c68e4536bf7c411d7a3ce5734111476` вернул HTTP 200.
- После запуска пользователь прислал скрин успешного запроса внутри Brev:
  `/v1/chat/completions`, HTTP 200, `content: "Модель работает.\n"`,
  `finish_reason: "stop"`, 6 выходных токенов. Это подтверждает простую генерацию;
  последующие проверки карточки, evidence и времени описаны выше.

В карточке модели NVIDIA приведён запуск через vLLM и указан параметр
`--mamba_ssm_cache_dtype float32`. Для отключения рассуждений используется
`/no_think` в системном сообщении. Пользователь успешно проверил этот режим через curl.
В `backend/app/ai/client.py` добавлено такое системное указание только для провайдера
`nvidia` с ID этой модели. Сообщения копируются, чтобы не изменять их для остальных
провайдеров. Изменённый клиент проверен через SSH-туннель.

Используется одна L40S с 48 GB VRAM. На скрине `nvidia-smi` видны L40S,
46068 MiB, драйвер 580.126.09; Docker сообщает версию 29.1.5.
В выводе `docker info` присутствует `nvidia-container-runtime`.
Результаты проверки JSON, evidence и времени приведены в начале документа.

Источники:

- [Официальная карточка NVIDIA Nemotron Nano 9B v2](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2)
- [NVIDIA: поддерживаемые модели и GPU в NIM](https://docs.nvidia.com/nim/large-language-models/1.12.0/supported-models.html)
- [Brev: управление экземплярами и оплатой](https://docs.nvidia.com/brev/guides/console-reference)

### План подключения к нашему проекту

1. Проверить итоговую конфигурацию предложения Brev, цену и доступ по SSH.
2. Подготовить команду vLLM с закреплённой версией и ревизией модели,
   ограничением контекста и числа параллельных запросов; согласовать расходы до аренды.
3. Запустить сервер на согласованной машине и дождаться готовности API.
4. Получить точный ID модели из `/v1/models` запущенного сервера.
5. Подключить API через приватный SSH-туннель. Например, локальный порт 9000
   можно направить на порт 8000 сервера модели; порт 8000 локального backend останется свободен.
6. В локальном `.env` задать адрес и ID реально работающей модели:

   ```dotenv
   NVIDIA_BASE_URL=http://127.0.0.1:9000/v1
   NVIDIA_MODEL=<id из ответа /v1/models>
   ```

7. Настроить `NVIDIA_API_KEY` в соответствии с аутентификацией своего сервера.
   Ключ NGC для скачивания контейнеров и ключ API сервера имеют разные назначения.
   В текущем клиенте NVIDIA включается только при непустом `NVIDIA_API_KEY`.
8. Проверить реальную генерацию, evidence, JSON и задержку на черновике Z0.

`backend/app/ai/client.py` уже читает `NVIDIA_BASE_URL` и `NVIDIA_MODEL`;
менять публичные схемы API для такого подключения не требуется.
При двух настроенных провайдерах текущая цепочка сначала вызывает OpenAI.
Прямую проверку NVIDIA следует выполнять отдельно, чтобы не принять ответ OpenAI
за успешный ответ NVIDIA.

### Текущее состояние

- На локальном компьютере обнаружена RTX 3050 Laptop с 6 GB VRAM.
- Пользователь создал платное окружение `taskready-nvidia` в Brev:
  MASSEDCOMPUTE (shadeform), L40S 48 GB, 1 GPU, 72 GB RAM, 12 CPU,
  SSD 625 GB, Fixed ports, No stop/start. Экран подтверждения показал
  $1.06/час итогом, Storage Included.
- По этой почасовой ставке 3 часа составят $3.18, 5 часов — $5.30,
  по показанной ставке. У предложения нет остановки/возобновления;
  после работы нужно сохранить нужные данные и удалить окружение.
- Генерация внутри Brev подтверждена скриншотом пользователя с HTTP 200.
- Команда запуска публикует API на `127.0.0.1:8000` машины Brev.
  Локальный компьютер подключён через прямой OpenSSH-туннель на порту 9000.
- В таблице TCP/UDP Ports не появилось правило после попытки добавления.
  Причина не установлена. При этом прямой SSH на внешнем адресе машины работает.
- На Windows используется `ssh.exe`; Brev CLI и отдельный дистрибутив Ubuntu
  не устанавливались. Ошибка штатного `ssh-keyscan` Windows обойдена использованием
  уже установленного `ssh-keyscan` из Git с проверкой отпечатка.
- В `.env` настроены адрес и модель Brev, но также заполнен ключ OpenAI.
  Для выбора NVIDIA используется отдельный скрипт запуска backend, описанный выше.

## Что делать сейчас

Для hosted Build: отправить подготовленное обращение в официальный канал поддержки.
Для собственного сервера: пользоваться подключённым backend; после перезагрузки
запустить два скрипта из начала документа. Отдельно остаётся оптимизировать
скорость и качество ответа для порога Z0 и проверить полный сценарий в UI.

Справка: [Brev CLI: установка и SSH](https://docs.nvidia.com/brev/cli/getting-started),
[Brev: port forwarding для API](https://docs.nvidia.com/brev/guides/inference-deployment/deploying-nims).
