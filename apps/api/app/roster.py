"""Supplied Krakoan roster fixture. Project-supplied sample data, not from Marvel."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

ROSTER_PATH = Path(os.environ.get("HOX_ROSTER", Path(__file__).resolve().parents[1] / "fixtures" / "krakoan_roster.json"))
SOURCE_NOTE = "Roster data supplied with the House of X demo project. Not provided by Marvel."


@lru_cache
def load_roster() -> dict:
    data = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    data["total_characters"] = sum(len(f["characters"]) for f in data["factions"])
    data["source_note"] = SOURCE_NOTE
    return data


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_entry(name: str) -> dict | None:
    """Match a Marvel character name against roster alias or name, with Kitty/Kate."""
    wanted = {_norm(name), _norm(name.replace("Kitty", "Kate"))}
    for faction in load_roster()["factions"]:
        for c in faction["characters"]:
            if wanted & {_norm(c["alias"]), _norm(c["name"])}:
                return {**c, "faction_name": faction["faction_name"]}
    return None
