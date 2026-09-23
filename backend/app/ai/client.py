"""Цепочка провайдеров OpenAI → NVIDIA Build → заглушка (AGENTS.md §8).

На каждом провайдере: ответ → json.loads → Pydantic; при ошибке разбора один повтор
с напоминанием о схеме, потом следующий провайдер. Ошибки API сразу ведут к следующему.
"""
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.ai.prompts import SCHEMA_REMINDER
from app.schemas import AiMode

logger = logging.getLogger(__name__)

TIMEOUT = 20
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_NVIDIA_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"
DEFAULT_NVIDIA_URL = "https://integrate.api.nvidia.com/v1"

Out = TypeVar("Out", bound=BaseModel)


@dataclass(frozen=True)
class Provider:
    name: AiMode
    api_key: str
    model: str
    base_url: str | None = None
    json_mode: bool = False


def _env(name: str, default: str = "") -> str:
    # .env допускает комментарий после значения: AI_MODE=auto  # auto | stub
    return os.getenv(name, "").split(" #")[0].strip() or default


def stub_mode() -> bool:
    return _env("AI_MODE", "auto").lower() == "stub"


def providers() -> list[Provider]:
    if stub_mode():
        return []
    chain = []
    if key := _env("OPENAI_API_KEY"):
        chain.append(Provider("openai", key, _env("OPENAI_MODEL", DEFAULT_OPENAI_MODEL), json_mode=True))
    if key := _env("NVIDIA_API_KEY"):
        chain.append(Provider(
            "nvidia", key, _env("NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL), _env("NVIDIA_BASE_URL", DEFAULT_NVIDIA_URL),
        ))
    return chain


def _chat(provider: Provider, messages: list[dict]) -> str:
    # Nemotron Nano v2 defaults to reasoning; request the final JSON directly.
    # Copy messages so this model-specific setting does not affect other providers.
    if provider.name == "nvidia" and provider.model.casefold() == "nvidia/nvidia-nemotron-nano-9b-v2":
        messages = [dict(message) for message in messages]
        for message in messages:
            if message.get("role") == "system":
                message["content"] = "/no_think\n" + message["content"]
                break
        else:
            messages.insert(0, {"role": "system", "content": "/no_think"})
    client = OpenAI(api_key=provider.api_key, base_url=provider.base_url, timeout=TIMEOUT, max_retries=1)
    extra = {"response_format": {"type": "json_object"}} if provider.json_mode else {}
    response = client.chat.completions.create(
        model=provider.model, messages=messages, temperature=0, max_tokens=1500, **extra,
    )
    return response.choices[0].message.content or ""


def _parse(raw: str, schema: type[Out]) -> Out:
    # Модели без JSON-режима любят оборачивать ответ в ```json … ```.
    match = re.search(r"\{.*\}", raw, re.S)
    return schema.model_validate(json.loads(match.group(0) if match else raw))


def complete_json(messages: list[dict], schema: type[Out]) -> tuple[Out, AiMode] | None:
    """Первый валидный ответ по цепочке провайдеров или None — тогда вызывающий берёт заглушку."""
    for provider in providers():
        attempt = list(messages)
        for try_number in (1, 2):
            try:
                raw = _chat(provider, attempt)
            except Exception as exc:
                logger.warning("ИИ %s (%s) недоступен: %s", provider.name, provider.model, exc)
                break
            try:
                return _parse(raw, schema), provider.name
            except Exception as exc:
                logger.warning("ИИ %s: невалидный ответ, попытка %d: %s", provider.name, try_number, str(exc)[:200])
                attempt = attempt + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": SCHEMA_REMINDER.format(error=str(exc)[:300])},
                ]
    return None
