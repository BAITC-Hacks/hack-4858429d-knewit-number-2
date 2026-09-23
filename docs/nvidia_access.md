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

## Путь 2. Собственный NVIDIA NIM на GPU в Brev

Это вариант развёртывания, предложенный для решения проблемы доступа.
В исходном AGENTS.md указан NVIDIA Build; собственный NIM меняет место запуска
модели. Если условия мероприятия требуют именно hosted Build, допустимость
замены нужно уточнить у лида/организаторов.

В Brev можно разместить NIM с OpenAI-совместимым API. Руководство Brev рекомендует
L40S 48 GB или A100 80 GB; конкретную GPU выбираем по модели и доступной цене.
Первый запуск требует загрузки контейнера и весов.

Для NGC-развёртывания документация NIM указывает Personal API Key с сервисом
NGC Catalog. Нужно отдельно проверить доступ к конкретному образу, его лицензии,
тегу и профилю оборудования. Наличие ключа само по себе не гарантирует загрузку
любого NIM. Требование Public API Endpoints относится к hosted inference API.

Источники:

- [NVIDIA Brev: развёртывание NIM](https://docs.nvidia.com/brev/guides/inference-deployment/deploying-nims)
- [NVIDIA NIM: требования и NGC-развёртывание](https://docs.nvidia.com/nim/large-language-models/1.12.0/getting-started.html)

### План подключения к нашему проекту

1. Узнать, есть ли уже машина в Brev, её GPU, объём VRAM и стоимость работы.
2. Выбрать подходящий NIM и проверить доступ к образу до выделения новой платной GPU.
3. Запустить контейнер на согласованной машине и дождаться готовности API.
4. Получить точный ID модели из `/v1/models` запущенного сервера.
5. Подключить API через приватный SSH-туннель. Например, локальный порт 9000
   можно направить на порт 8000 NIM; порт 8000 локального backend останется свободен.
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
  Этого недостаточно, чтобы без проверки обещать запуск выбранного NIM.
- Тип GPU и состояние машины Brev пока неизвестны.
- Адрес рабочего NIM, ID модели и доступ к конкретному образу ещё не подтверждены.
- Платные ресурсы не создавались; конфигурация проекта и ключи не менялись.

## Что делать сейчас

Для hosted Build: отправить подготовленное обращение в официальный канал поддержки.
Для собственного сервера: сообщить тип уже имеющейся GPU в Brev или отсутствие машины.
После этого можно подготовить конкретную команду запуска и оценить стоимость.
