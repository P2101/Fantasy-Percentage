"""Interfaz local para gestionar tus jugadores de Fantasy.

Ejecuta: python app.py
Después abre: http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import unicodedata
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).parent
FANTASY_FILE = BASE_DIR / "fantasy.json"
MY_PLAYERS_FILE = BASE_DIR / "mis_jugadores.json"
UPDATER_SCRIPT = BASE_DIR / "fantasy-mcp.py"
UPDATE_LOCK = threading.Lock()


def normalized_name(name: str) -> str:
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", name)
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_accents.casefold().split())


def read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def available_players() -> dict[str, dict[str, object]]:
    fantasy = read_json(FANTASY_FILE, {"teams": []})
    players: dict[str, dict[str, object]] = {}
    for team in fantasy.get("teams", []):
        for player in team.get("players", []):
            item = {
                "name": player["name"],
                "team": team["name"],
                "probability": player["probability"],
            }
            players[normalized_name(player["name"])] = item
    return players


def my_players() -> list[str]:
    return read_json(MY_PLAYERS_FILE, {"players": []}).get("players", [])


def player_view() -> list[dict[str, object]]:
    available = available_players()
    result = []
    for name in my_players():
        player = available.get(normalized_name(name))
        result.append(
            {"name": name, "found": False, "team": "—", "probability": None}
            if player is None
            else {"found": True, **player}
        )
    return sorted(result, key=lambda player: (player["probability"] is None, -(player["probability"] or 0), player["name"]))


def write_my_players(players: list[str]) -> None:
    MY_PLAYERS_FILE.write_text(
        json.dumps({"players": players}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/api/players":
            self.send_json({"players": player_view()})
        elif route == "/api/catalog":
            self.send_json({"players": sorted(available_players().values(), key=lambda player: player["name"])})
        elif route == "/":
            content = (BASE_DIR / "index.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/api/refresh":
            if not UPDATE_LOCK.acquire(blocking=False):
                self.send_json({"error": "Ya hay una actualización en curso."}, HTTPStatus.CONFLICT)
                return
            try:
                result = subprocess.run(
                    [sys.executable, str(UPDATER_SCRIPT)],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=180,
                )
            except subprocess.TimeoutExpired:
                self.send_json({"error": "La actualización ha tardado demasiado tiempo."}, HTTPStatus.GATEWAY_TIMEOUT)
            except OSError as error:
                self.send_json({"error": f"No se pudo iniciar la actualización: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            else:
                if result.returncode != 0:
                    detail = result.stderr.strip() or result.stdout.strip()
                    self.send_json({"error": f"La actualización falló. {detail}".strip()}, HTTPStatus.INTERNAL_SERVER_ERROR)
                else:
                    self.send_json({"message": "Probabilidades actualizadas."})
            finally:
                UPDATE_LOCK.release()
            return

        if route != "/api/players":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            requested_name = str(self.read_body()["name"]).strip()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.send_json({"error": "Indica un jugador válido."}, HTTPStatus.BAD_REQUEST)
            return

        player = available_players().get(normalized_name(requested_name))
        if player is None:
            self.send_json({"error": "El jugador no aparece en fantasy.json."}, HTTPStatus.BAD_REQUEST)
            return
        players = my_players()
        if normalized_name(player["name"]) in {normalized_name(name) for name in players}:
            self.send_json({"error": "Ese jugador ya está en tu lista."}, HTTPStatus.CONFLICT)
            return
        players.append(player["name"])
        write_my_players(players)
        self.send_json({"players": player_view()}, HTTPStatus.CREATED)

    def do_DELETE(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/players":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            name = str(self.read_body()["name"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.send_json({"error": "Indica el jugador a eliminar."}, HTTPStatus.BAD_REQUEST)
            return
        players = my_players()
        filtered = [player for player in players if normalized_name(player) != normalized_name(name)]
        if len(filtered) == len(players):
            self.send_json({"error": "No se ha encontrado el jugador."}, HTTPStatus.NOT_FOUND)
            return
        write_my_players(filtered)
        self.send_json({"players": player_view()})

    def log_message(self, format: str, *args: object) -> None:
        print(format % args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Vista disponible en http://127.0.0.1:8000")
    server.serve_forever()
