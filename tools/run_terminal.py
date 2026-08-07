#!/usr/bin/env python3
"""Play any refactored game in a terminal.

This is the regression test for the refactor: run a game here, play the
original in `terminal-games/` beside it, and the two should read the same.

    python tools/run_terminal.py                 # list the games
    python tools/run_terminal.py secret-number   # play one
    python tools/run_terminal.py secret-number --seed 7
    python tools/run_terminal.py secret-number --verbose   # show score/sound

It drives the same `engine.py` the browser drives, so a game that plays
here is a game that will play there.
"""

import argparse
import os
import sys

# Everything in public/ is deployed verbatim, so nothing may drop a
# __pycache__ in there — a stale .pyc of a deleted game would ship.
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
PY_DIR = os.path.join(os.path.dirname(HERE), "public", "py")
sys.path.insert(0, PY_DIR)

# The games are emoji-heavy; a cp1252 console would crash on the first tile.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
        pass

import engine  # noqa: E402  (path must be set first)

INDENT = "  "


def show(view: dict, verbose: bool) -> None:
    # lines first, then art: art is the picture of where you now stand,
    # and it belongs directly above the question about it.
    if view.get("lines"):
        print()
        for line in view["lines"]:
            print(INDENT + line)
    if view.get("art"):
        print()
        for line in str(view["art"]).split("\n"):
            print(INDENT + line)
    if verbose:
        bits = []
        if view.get("score") is not None:
            bits.append(f"score={view['score']}")
        if view.get("sound"):
            bits.append(f"sound={view['sound']}")
        if bits:
            print(INDENT + "[" + " ".join(bits) + "]")
    print()


def ask(prompt: dict) -> str | None:
    """Return the string to send, or None to quit the runner."""
    kind = prompt.get("kind")
    label = prompt.get("label") or ""

    if kind == "continue":
        _read(INDENT + (label or "Press Enter to continue") + " ")
        return ""

    if kind == "choice":
        choices = prompt.get("choices") or []
        if label:
            print(INDENT + label)
        for choice in choices:
            key = choice["value"] if choice["value"] != "" else "(Enter)"
            print(f"{INDENT}  {key} - {choice['label']}")
        return _read(INDENT + "> ")

    if kind == "number":
        lo, hi = prompt.get("min"), prompt.get("max")
        hint = f" ({lo}-{hi})" if lo is not None and hi is not None else ""
        return _read(INDENT + (label or "Number") + hint + " ")

    if kind == "text":
        return _read(INDENT + (label or "Answer") + " ")

    if kind == "end":
        answer = _read(INDENT + (label or "Play again?") + " (y/n) ")
        if answer is None:
            return None
        return "__again__" if answer.strip().lower().startswith("y") else None

    print(INDENT + f"[unknown prompt kind {kind!r} — stopping]")
    return None


def _read(text: str) -> str | None:
    try:
        return input(text)
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def play(game_id: str, seed, verbose: bool) -> int:
    eng = engine.Engine()
    view = eng.start(game_id, seed)
    if not view.get("ok"):
        show(view, verbose)
        print(INDENT + (view.get("detail") or "").strip())
        return 1

    while True:
        show(view, verbose)
        prompt = view.get("prompt") or {}
        answer = ask(prompt)
        if answer is None:
            print(INDENT + "Bye!\n")
            return 0
        if answer == "__again__":
            view = eng.restart(seed)
        else:
            view = eng.send(answer)


def main() -> int:
    parser = argparse.ArgumentParser(description="Play a Boo's Game Box game in the terminal.")
    parser.add_argument("game", nargs="?", help="game id, e.g. secret-number")
    parser.add_argument("--seed", type=int, default=None, help="seed the RNG for a repeatable game")
    parser.add_argument("--verbose", action="store_true", help="show score and sound hints")
    args = parser.parse_args()

    try:
        games = engine.catalog()
    except engine.RegistryError as exc:
        print(f"Registry problem: {exc}")
        return 1

    if not args.game:
        print("\n  Boo's Game Box — games in the box:\n")
        for game in games:
            print(f"    {game['emoji']}  {game['id']:<16} {game['title']} — {game['blurb']}")
        print(f"\n  python {os.path.relpath(__file__)} <id>\n")
        return 0

    if args.game not in [g["id"] for g in games]:
        print(f"No game called {args.game!r}. Run without arguments to see the list.")
        return 1

    return play(args.game, args.seed, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
