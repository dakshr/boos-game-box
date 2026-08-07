"""Loader and event router.

Runs inside Pyodide in the browser, and inside CPython for the terminal
runner and the validator — the same code path either way, which is what
makes `tools/run_terminal.py` a real regression test.

Responsibilities:
  * read `games.json`, import each module, expose a catalog
  * hold one live game instance and route `send()` to it
  * turn `View` objects into plain dicts / JSON for the JS bridge
  * never let an exception from game code escape to the page

The registry is the only place a game is named. Nothing in this file
mentions a specific game.
"""

import importlib
import json
import os
import sys
import traceback
from dataclasses import asdict

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "games.json")

# Games do `from view import View, Prompt` — make that importable no matter
# who imported us or from where.
if HERE not in sys.path:
    sys.path.insert(0, HERE)

REQUIRED_META = ("ID", "TITLE", "BLURB", "EMOJI", "MIN_AGE")


class RegistryError(Exception):
    """A registered game does not exist, or does not match its ID."""


def module_name(game_id: str) -> str:
    """'counting-caterpillar' -> 'counting_caterpillar'. The only naming rule."""
    return game_id.replace("-", "_")


def registered_ids() -> list[str]:
    with open(REGISTRY, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    ids = data.get("games")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise RegistryError("games.json must contain a 'games' array of strings")
    return ids


def load_module(game_id: str):
    """Import one game module and check it against the registry.

    Loud on mismatch, deliberately: a game whose ID drifts from its filename
    is the kind of bug that only shows up on the child's device.
    """
    name = f"games.{module_name(game_id)}"
    try:
        module = importlib.import_module(name)
    except ImportError as exc:
        raise RegistryError(
            f"games.json registers {game_id!r} but {name.replace('.', '/')}.py "
            f"could not be imported: {exc}"
        ) from exc

    for const in REQUIRED_META:
        if not hasattr(module, const):
            raise RegistryError(f"{name} is missing required constant {const}")
    if module.ID != game_id:
        raise RegistryError(
            f"{name}.ID is {module.ID!r} but games.json registers {game_id!r} — "
            f"these must match"
        )
    if not hasattr(module, "Game"):
        raise RegistryError(f"{name} has no Game class")
    return module


def catalog() -> list[dict]:
    """Everything the picker screen needs, in registry order."""
    out = []
    for game_id in registered_ids():
        module = load_module(game_id)
        out.append(
            {
                "id": module.ID,
                "title": module.TITLE,
                "blurb": module.BLURB,
                "emoji": module.EMOJI,
                "min_age": module.MIN_AGE,
            }
        )
    return out


def view_to_dict(view) -> dict:
    """Serialize a View for the JS bridge. Tolerates a game that returns
    something View-shaped but not a real View."""
    try:
        data = asdict(view)
    except TypeError:
        data = {
            "lines": list(getattr(view, "lines", [])),
            "prompt": asdict(view.prompt),
            "art": getattr(view, "art", None),
            "sound": getattr(view, "sound", None),
            "score": getattr(view, "score", None),
        }
    data["ok"] = True
    return data


def error_view(message: str, detail: str = "") -> dict:
    """What the child sees when a game misbehaves. Never a stack trace."""
    if detail:
        sys.stderr.write(detail + "\n")
    return {
        "ok": False,
        "lines": [
            "Oh no — that game got its wires crossed.",
            message,
        ],
        "prompt": {
            "kind": "end",
            "label": "",
            "choices": [],
            "min": None,
            "max": None,
        },
        "art": "🧩",
        "sound": None,
        "score": None,
        "detail": detail,
    }


def clean_seed(seed):
    """The JS bridge can hand us all sorts of things — JsNull, undefined, a
    float, a string. Only an int is a seed; everything else means 'no seed'."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        return None
    return seed


class Engine:
    """Holds the one live game. One engine per page."""

    def __init__(self) -> None:
        self.game = None
        self.game_id = None

    def start(self, game_id: str, seed=None) -> dict:
        seed = clean_seed(seed)
        try:
            module = load_module(game_id)
        except RegistryError as exc:
            return error_view("That game isn't in the box.", str(exc))
        try:
            self.game = module.Game(seed)
            self.game_id = game_id
            return view_to_dict(self.game.start())
        except Exception:
            self.game = None
            self.game_id = None
            return error_view("It couldn't get started.", traceback.format_exc())

    def send(self, value) -> dict:
        if self.game is None:
            return error_view("No game is running.", "send() before start()")
        if isinstance(value, str):
            text = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            text = str(value)
        else:  # None, JsNull, undefined, a proxy of something odd
            text = ""
        try:
            return view_to_dict(self.game.send(text))
        except Exception:
            return error_view("It got stuck on that answer.", traceback.format_exc())

    def restart(self, seed=None) -> dict:
        if self.game_id is None:
            return error_view("No game is running.", "restart() before start()")
        return self.start(self.game_id, seed)


ENGINE = Engine()


# --- JSON bridge -------------------------------------------------------
# JS calls these and parses the result. Strings cross the boundary cleanly;
# proxied Python objects do not.


def catalog_json() -> str:
    try:
        return json.dumps({"ok": True, "games": catalog()})
    except Exception as exc:
        return json.dumps(
            {"ok": False, "error": str(exc), "detail": traceback.format_exc()}
        )


def start_json(game_id: str, seed=None) -> str:
    return json.dumps(ENGINE.start(game_id, seed))


def send_json(value: str) -> str:
    return json.dumps(ENGINE.send(value))


def restart_json(seed=None) -> str:
    return json.dumps(ENGINE.restart(seed))
