# NVIDIA: восстановление доступа и вариант запуска через Brev

Проверено 23 сентября 2026 года. Документ не содержит ключей доступа.

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

Теперь рассматриваем открытую модель `nvidia/NVIDIA-Nemotron-Nano-9B-v2`
из официального репозитория NVIDIA на Hugging Face, запуск через vLLM.
Это собственный сервер с OpenAI-совместимым API. Развёртывание через vLLM
не следует обозначать как NVIDIA NIM или hosted Build.

Проверено без ключа Hugging Face:

- API метаданных вернул HTTP 200 и `gated: false`.
- HEAD первого файла весов в ревизии
  `6533e8de2c68e4536bf7c411d7a3ce5734111476` вернул HTTP 200.
- Полные веса ещё не скачаны, генерация на GPU ещё не проверена.

В карточке модели NVIDIA приведён запуск через vLLM и указан параметр
`--mamba_ssm_cache_dtype float32`. Для отключения рассуждений используется
`/no_think` в системном сообщении. Его потребуется учесть при настройке клиента;
сейчас соответствующее изменение в код не внесено.

Планируем одну L40S с 48 GB VRAM. NVIDIA указывает такую конфигурацию среди
проверенных для этой модели в NIM; это основание для выбора оборудования,
а не результат проверки нашего сервера vLLM. Качество русского JSON, evidence
и задержку менее 5 секунд нужно измерить после запуска.

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

### Текущее состояние подготовки

- На локальном компьютере обнаружена RTX 3050 Laptop с 6 GB VRAM.
- На скриншоте Brev нет созданных окружений. Пользователь открыл Create Environment
  и выбрал L40S, 48 GB VRAM, 1 GPU.
- Видимое предложение MASSEDCOMPUTE (shadeform): $1.06/час, 72 GB RAM,
  12 CPU, SSD 625 GB, Fixed ports, No stop/start. Это цена со скриншота,
  окончательную сумму и дополнительные начисления нужно проверить перед запуском.
- По этой почасовой ставке 3 часа составят $3.18, 5 часов — $5.30,
  без возможных дополнительных начислений. У предложения нет остановки/возобновления;
  после работы нужно сохранить нужные данные и удалить окружение.
- Адрес работающего сервера и результат генерации ещё не получены.
- Платные ресурсы не создавались; конфигурация проекта и ключи не менялись.

## Что делать сейчас

Для hosted Build: отправить подготовленное обращение в официальный канал поддержки.
Для собственного сервера: перейти от выбранного предложения к настройкам окружения
и проверить экран конфигурации и итоговую стоимость до платного запуска.
