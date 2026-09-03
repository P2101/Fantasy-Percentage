"""Cruza tus jugadores con las probabilidades de ``fantasy.json``."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).parent
FANTASY_FILE = BASE_DIR / "fantasy.json"
MY_PLAYERS_FILE = BASE_DIR / "mis_jugadores.json"
OUTPUT_FILE = BASE_DIR / "mis_probabilidades.json"


def normalized_name(name: str) -> str:
    """Compara nombres sin distinguir mayúsculas, tildes ni espacios extra."""
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", name)
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_accents.casefold().split())


def main() -> None:
    fantasy: dict[str, Any] = json.loads(FANTASY_FILE.read_text(encoding="utf-8"))
    my_players: dict[str, list[str]] = json.loads(MY_PLAYERS_FILE.read_text(encoding="utf-8"))

    players_by_name: dict[str, dict[str, Any]] = {}
    for team in fantasy.get("teams", []):
        for player in team.get("players", []):
            players_by_name[normalized_name(player["name"])] = {
                "team": team["name"],
                "name": player["name"],
                "probability": player["probability"],
            }

    results = []
    for requested_name in my_players.get("players", []):
        player = players_by_name.get(normalized_name(requested_name))
        results.append(
            {"name": requested_name, "found": False, "probability": None}
            if player is None
            else {"name": requested_name, "found": True, **player}
        )

    result = {
        "fantasy_generated_at": fantasy.get("generated_at"),
        "players": results,
    }
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    for player in results:
        probability = player["probability"]
        if probability is None:
            print(f"{player['name']}: no encontrado")
        else:
            print(f"{player['name']} ({player['team']}): {probability}%")
    print(f"JSON guardado en: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
