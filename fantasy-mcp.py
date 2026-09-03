"""Extrae las probabilidades de titularidad de los equipos de LaLiga.

Genera un archivo ``fantasy.json`` junto a este script.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://www.futbolfantasy.com/laliga/equipos/"
EQUIPOS = [
    "alaves", "athletic", "atletico", "barcelona", "celta", "deportivo",
    "elche", "espanyol", "getafe", "levante", "malaga", "osasuna", "racing",
    "rayo-vallecano", "betis", "real-madrid", "real-sociedad", "sevilla",
    "valencia", "villarreal",
]
OUTPUT_FILE = Path(__file__).with_name("fantasy.json")


class EquipoParser(HTMLParser):
    """Lee la lista de jugadores que la página incluye en su HTML."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.team_name = ""
        self._inside_title = False
        self._current_player: dict[str, Any] | None = None
        self._player_depth: int | None = None
        self.players: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag not in self.VOID_TAGS:
            self.tags.append(tag)
        if tag == "title":
            self._inside_title = True

        classes = set((attributes.get("class") or "").split())
        if tag == "div" and "jugador" in classes and "tipo_lista" in classes:
            probability = (attributes.get("data-probabilidad") or "").strip()
            player_slug = attributes.get("data-nombre")
            probability_value = probability.removesuffix("%").strip()
            if player_slug and probability_value.isdecimal():
                self._current_player = {
                    "name": player_slug,
                    "probability": int(probability_value),
                }
                self._player_depth = len(self.tags)

        if self._current_player is not None and tag == "img":
            # El atributo alt conserva mayúsculas y tildes del nombre público.
            # "Fuera" pertenece al icono de localización, no al jugador.
            display_name = (attributes.get("alt") or "").strip()
            if display_name and display_name.casefold() != "fuera":
                self._current_player["name"] = display_name

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
        if self._current_player is not None and tag == "div" and self._player_depth == len(self.tags):
            self.players.append(self._current_player)
            self._current_player = None
            self._player_depth = None
        if tag not in self.VOID_TAGS and self.tags:
            self.tags.pop()

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self.team_name += data


def fetch_team(slug: str) -> dict[str, Any]:
    """Descarga y transforma una página de equipo."""
    url = f"{BASE_URL}{slug}"
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; fantasy-data-export/1.0)",
            "Accept-Language": "es-ES,es;q=0.9",
        },
    )
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = EquipoParser()
    parser.feed(html)
    parser.close()
    # Evita repeticiones si la web ofrece más de una representación del listado.
    players = list({player["name"]: player for player in parser.players}.values())
    return {
        "name": parser.team_name.split(" - ", maxsplit=1)[0].strip() or slug,
        "slug": slug,
        "url": url,
        "players": players,
    }


def main() -> None:
    result: dict[str, Any] = {
        "source": "FutbolFantasy",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "teams": [],
        "errors": [],
    }
    for slug in EQUIPOS:
        try:
            team = fetch_team(slug)
            result["teams"].append(team)
            print(f"{team['name']}: {len(team['players'])} jugadores")
        except HTTPError as error:
            result["errors"].append({"team": slug, "error": f"HTTP {error.code}"})
            print(f"{slug}: HTTP {error.code}")
        except URLError as error:
            result["errors"].append({"team": slug, "error": str(error.reason)})
            print(f"{slug}: no se pudo conectar ({error.reason})")
        sleep(1)  # Peticiones moderadas para no sobrecargar el origen.

    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON guardado en: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
