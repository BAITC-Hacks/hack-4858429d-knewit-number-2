"""Explicit demo reset: python -m app.reset_db (stop uvicorn first)."""

import argparse
from pathlib import Path

from app import db


def main() -> int:
    parser = argparse.ArgumentParser(description="Очистить локальную SQLite БД и заново загрузить seed.")
    parser.add_argument("--yes", action="store_true", help="Подтвердить удаление всех задач, команд и откликов")
    args = parser.parse_args()
    if db.engine.dialect.name != "sqlite":
        parser.error("Сброс разрешён только для локальной SQLite БД")
    database = db.engine.url.database
    target = ":memory:" if database in (None, "", ":memory:") else str(Path(database).resolve())
    print(f"БД: {target}")
    print("Все задачи, команды и отклики будут удалены. Перед сбросом остановите сервер.")
    if not args.yes:
        try:
            confirmed = input("Введите RESET для подтверждения: ").strip() == "RESET"
        except (EOFError, KeyboardInterrupt):
            confirmed = False
        if not confirmed:
            print("Сброс отменён.")
            return 1
    try:
        db.reset_database()
    except Exception:
        print("Сброс не выполнен. Подробности в предупреждении выше; прежние данные сохранены.")
        return 1
    print("Seed загружен. Можно запускать сервер.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
