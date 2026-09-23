import pytest


@pytest.fixture(autouse=True)
def offline_ai(monkeypatch):
    # Тесты не ходят в настоящие LLM, даже если в .env есть ключи. Тесты цепочки
    # провайдеров сами ставят AI_MODE=auto и мокают client._chat.
    monkeypatch.setenv("AI_MODE", "stub")
