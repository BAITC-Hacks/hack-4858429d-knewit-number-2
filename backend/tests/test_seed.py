import json
import re
from pathlib import Path

from app.schemas import DraftExample, ProposalCreate, TaskCard

SEED = Path(__file__).resolve().parents[1] / "seed"
INDUSTRIES = {"Ритейл", "HoReCa", "Образование", "Финансы", "Медицина", "Логистика", "IT", "Производство", "Госсектор", "Другое"}


def load(name: str) -> list[dict]:
    return json.loads((SEED / name).read_text(encoding="utf-8"))


def test_drafts():
    drafts = [DraftExample.model_validate(item) for item in load("drafts.json")]
    assert len(drafts) == 5 and len({d.id for d in drafts}) == 5
    assert {d.completeness for d in drafts} == {"low", "medium", "high"}
    assert all(d.industry in INDUSTRIES and 20 <= len(d.text) <= 3000 for d in drafts)


def test_cards():
    cards = load("cards.json")
    assert len(cards) == 5
    for item in cards:
        assert item["business_name"] and item["industry"] in INDUSTRIES
        card = TaskCard.model_validate(item["card"])
        assert 3 <= len(card.title) <= 120
        assert re.fullmatch(r"[A-Za-z0-9._%+-]+@example\.com", card.contact)
    assert [item["expected_score"] for item in cards] == sorted((item["expected_score"] for item in cards), reverse=True)


def test_teams_and_proposals():
    teams, proposals = load("teams.json"), load("proposals.json")
    assert len(teams) == 5 and "DataCats" in {team["name"] for team in teams}
    assert all(team["interests"] and team["skills"] and team["technologies"] for team in teams)
    assert len(proposals) == 5
    for item in proposals:
        assert 0 <= item["task_index"] < 5 and 0 <= item["team_index"] < len(teams)
        ProposalCreate.model_validate({**item, "team_id": 1})
