from app.schemas import NextLevel, Rating, TaskCard


def compute_rating(card: TaskCard) -> Rating:
    # ponytail: временная оценка 0; заменить формулой из AGENTS.md §7.
    return Rating(
        total=0,
        level="draft",
        level_label="Черновик · требует уточнения",
        categories=[],
        missing=[],
        next_level=NextLevel(level="working", label="Рабочая", threshold=40, points_needed=40),
    )
