#!/usr/bin/env python3
"""The pre-deploy gate.

Validates every game registered in `public/py/games.json` against the
contract in `public/py/view.py`:

  * the module imports, and its ID matches the registry
  * the required metadata constants exist and have sane types
  * `Game(seed)` constructs, `start()` returns a real View
  * `start()` twice on one seed gives two identical fresh games
  * two games with the same seed play identically
  * `send()` survives a fuzz of junk strings without raising
  * the source contains no `input()`, `print()`, `time.sleep()`,
    `sys.exit()`, `os.*`, and no module-level lowercase globals
  * nothing outside the standard library is imported

    python tools/check_games.py            # check everything
    python tools/check_games.py math-garden
    python tools/check_games.py --fuzz 2000

Exit code 0 means deployable.
"""

import argparse
import ast
import os
import random
import sys
import traceback

# public/ is deployed verbatim: never leave a __pycache__ behind in it.
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY_DIR = os.path.join(ROOT, "public", "py")
GAMES_DIR = os.path.join(PY_DIR, "games")
sys.path.insert(0, PY_DIR)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass

import engine  # noqa: E402
from view import Choice, Prompt, View  # noqa: E402

VALID_KINDS = {"choice", "number", "text", "continue", "end"}

BANNED_NAMES = {"input", "print", "exit", "quit", "eval", "exec", "open", "breakpoint"}
BANNED_MODULES = {"os", "sys", "time", "subprocess", "socket", "threading", "asyncio"}

# The junk a four-year-old, a fuzzer, or a broken keyboard can produce.
JUNK = [
    "",
    " ",
    "\n",
    "\t   \n",
    "abc",
    "ABC",
    "-1",
    "0",
    "0.5",
    "1e10",
    "999999999999999999999",
    "9" * 5000,
    "a" * 10000,
    "🐶",
    "😀" * 200,
    "١٢٣",
    "None",
    "null",
    "undefined",
    "[]",
    "{}",
    "1,2",
    "1 2",
    "0x10",
    "-0",
    "+3",
    " 4 ",
    "q",
    "quit",
    "yes",
    "no",
    "<script>alert(1)</script>",
    "'; DROP TABLE games; --",
    "%s%n",
    "\x00",
]


class Failure(Exception):
    pass


def check(condition, message):
    if not condition:
        raise Failure(message)


# --- static source checks ---------------------------------------------


def source_checks(game_id: str, path: str) -> list[str]:
    """Read the module as text. Catches what runtime checks can't."""
    notes = []
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source, filename=path)

    stdlib = set(sys.stdlib_module_names)
    allowed_local = {"view"}

    for node in ast.walk(tree):
        # --- imports ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                check(
                    top in stdlib or top in allowed_local,
                    f"imports {alias.name!r}, which is not in the standard library",
                )
                check(
                    top not in BANNED_MODULES,
                    f"imports {top!r} — games must not touch the outside world",
                )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise Failure("uses a relative import; games import `view` directly")
            top = (node.module or "").split(".")[0]
            check(
                top in stdlib or top in allowed_local,
                f"imports from {node.module!r}, which is not in the standard library",
            )
            check(
                top not in BANNED_MODULES,
                f"imports from {top!r} — games must not touch the outside world",
            )

        # --- banned calls ---
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BANNED_NAMES:
                raise Failure(f"calls {func.id}() on line {node.lineno}")
            if isinstance(func, ast.Attribute):
                owner = func.value
                if isinstance(owner, ast.Name):
                    dotted = f"{owner.id}.{func.attr}"
                    if owner.id == "random" and func.attr != "Random":
                        raise Failure(
                            f"calls {dotted}() on line {node.lineno} — use "
                            f"self.rng, a random.Random(seed) instance"
                        )
                    if owner.id in BANNED_MODULES:
                        raise Failure(f"calls {dotted}() on line {node.lineno}")

    # --- module-level state ---
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target]
        for target in targets:
            check(
                target.id.isupper() or target.id.startswith("_"),
                f"has a lowercase module-level variable {target.id!r} — all "
                f"per-player state must live on the instance",
            )

    if "\t" in source:
        notes.append("contains tab characters")
    return notes


# --- runtime contract checks ------------------------------------------


def validate_view(obj, where: str) -> View:
    check(isinstance(obj, View), f"{where} returned {type(obj).__name__}, not a View")
    check(isinstance(obj.lines, list), f"{where}: View.lines must be a list")
    for line in obj.lines:
        check(isinstance(line, str), f"{where}: every line must be a str, got {line!r}")
    prompt = obj.prompt
    check(isinstance(prompt, Prompt), f"{where}: View.prompt must be a Prompt")
    check(
        prompt.kind in VALID_KINDS,
        f"{where}: prompt.kind {prompt.kind!r} is not one of {sorted(VALID_KINDS)}",
    )
    check(isinstance(prompt.label, str), f"{where}: prompt.label must be a str")
    check(isinstance(prompt.choices, list), f"{where}: prompt.choices must be a list")
    for choice in prompt.choices:
        check(isinstance(choice, Choice), f"{where}: choices must be Choice objects")
        check(
            isinstance(choice.label, str) and isinstance(choice.value, str),
            f"{where}: Choice.label and Choice.value must both be str",
        )
    if prompt.kind == "choice":
        check(prompt.choices, f"{where}: a 'choice' prompt with no choices is a dead end")
    for field_name in ("min", "max"):
        value = getattr(prompt, field_name)
        check(
            value is None or isinstance(value, int),
            f"{where}: prompt.{field_name} must be an int or None",
        )
    check(
        obj.art is None or isinstance(obj.art, str), f"{where}: View.art must be str/None"
    )
    check(
        obj.sound is None or isinstance(obj.sound, str),
        f"{where}: View.sound must be str/None",
    )
    check(
        obj.score is None or isinstance(obj.score, int),
        f"{where}: View.score must be int/None",
    )
    # It must survive the JSON bridge.
    engine.view_to_dict(obj)
    return obj


def safe_send(game, value: str, context: str = ""):
    """send() is total. Prove it, and say so plainly when it isn't."""
    try:
        return game.send(value)
    except Exception as exc:
        where = f" {context}" if context else ""
        raise Failure(
            f"send({value[:40]!r}) raised {type(exc).__name__}: {exc}{where}\n"
            f"send() must never raise — return a View that re-prompts instead\n"
            + "".join(traceback.format_exc().splitlines(True)[-4:])
        ) from exc


def fuzz(module, steps: int, seed: int) -> None:
    """Walk the game like a toddler with a keyboard."""
    rng = random.Random(seed)
    game = module.Game(seed)
    view = validate_view(game.start(), "start()")

    for step in range(steps):
        choices = view.prompt.choices
        if choices and rng.random() < 0.6:
            value = rng.choice(choices).value
        else:
            value = rng.choice(JUNK)
        view = safe_send(game, value, f"at fuzz step {step}")
        validate_view(view, f"send({value[:40]!r})")


def determinism(module) -> None:
    """Same seed, same game. Twice."""
    a, b = module.Game(1234), module.Game(1234)
    va, vb = a.start(), b.start()
    check(va.lines == vb.lines, "two Game(1234) instances open differently")

    script = ["1", "2", "3", "5", "yes", "", "4", "q"]
    for value in script:
        check(
            safe_send(a, value).lines == safe_send(b, value).lines,
            f"two Game(1234) instances diverged after send({value!r}) — "
            f"something is using unseeded randomness",
        )

    # start() twice must give two identical fresh games
    solo = module.Game(99)
    first = solo.start()
    for value in script[:4]:
        safe_send(solo, value)
    second = solo.start()
    check(
        first.lines == second.lines and first.prompt == second.prompt,
        "start() is not idempotent — 'play again' would hand back a used game",
    )


def check_game(game_id: str, fuzz_steps: int) -> tuple[bool, list[str]]:
    notes: list[str] = []
    try:
        # Static checks first: a module that imports the wrong thing should
        # be told *what* it imported, not just that the import failed.
        path = os.path.join(GAMES_DIR, engine.module_name(game_id) + ".py")
        check(os.path.exists(path), f"expected {os.path.relpath(path, ROOT)} to exist")
        notes += source_checks(game_id, path)

        module = engine.load_module(game_id)

        check(isinstance(module.TITLE, str) and module.TITLE, "TITLE must be a non-empty str")
        check(isinstance(module.BLURB, str) and module.BLURB, "BLURB must be a non-empty str")
        check(isinstance(module.EMOJI, str) and module.EMOJI, "EMOJI must be a non-empty str")
        check(isinstance(module.MIN_AGE, int), "MIN_AGE must be an int")
        check(module.ID == module.ID.lower(), "ID must be lower-case")
        check(
            module.ID.replace("-", "").isalnum(),
            "ID must be kebab-case: letters, digits and hyphens only",
        )
        check(len(module.TITLE) <= 24, "TITLE is too long for a game tile (24 chars max)")
        check(len(module.BLURB) <= 80, "BLURB is too long for a game tile (80 chars max)")

        game = module.Game(None)
        check(hasattr(game, "start") and callable(game.start), "Game has no start()")
        check(hasattr(game, "send") and callable(game.send), "Game has no send()")
        validate_view(game.start(), "start()")

        determinism(module)
        fuzz(module, fuzz_steps, seed=7)

        # and the engine's own path, since that's what the browser uses
        eng = engine.Engine()
        started = eng.start(game_id, 5)
        check(started.get("ok"), f"engine.start() returned an error view: {started}")
        check(eng.send("1").get("ok"), "engine.send() returned an error view")

        return True, notes
    except Failure as exc:
        return False, [str(exc)]
    except engine.RegistryError as exc:
        return False, [str(exc)]
    except Exception:
        return False, [traceback.format_exc()]


def project_checks() -> list[str]:
    """Things that are not a game but will still break the deploy."""
    problems = []
    public = os.path.join(ROOT, "public")

    for name in (
        "index.html",
        "styles.css",
        "app.js",
        "sw.js",
        "manifest.json",
        "icons/icon-192.png",
        "icons/icon-512.png",
        "icons/icon-maskable-512.png",
    ):
        if not os.path.exists(os.path.join(public, *name.split("/"))):
            problems.append(f"public/{name} is missing")

    # public/ ships verbatim, so anything sitting in it goes to production.
    for dirpath, dirnames, _filenames in os.walk(public):
        if "__pycache__" in dirnames:
            problems.append(
                f"{os.path.relpath(os.path.join(dirpath, '__pycache__'), ROOT)} exists "
                f"— delete it; compiled bytecode of deleted games must not deploy"
            )

    try:
        registered = set(engine.registered_ids())
        on_disk = {
            name[:-3].replace("_", "-")
            for name in os.listdir(GAMES_DIR)
            if name.endswith(".py") and name != "__init__.py"
        }
        for orphan in sorted(on_disk - registered):
            problems.append(
                f"public/py/games/{orphan.replace('-', '_')}.py is not registered in "
                f"games.json — add it or delete it"
            )
    except OSError:
        pass

    def pinned(filename, variable):
        path = os.path.join(public, filename)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith(f"const {variable}"):
                    return line.split('"')[1] if '"' in line else None
        return None

    app_version = pinned("app.js", "PYODIDE_VERSION")
    sw_version = pinned("sw.js", "PYODIDE_VERSION")
    if app_version and sw_version and app_version != sw_version:
        problems.append(
            f"PYODIDE_VERSION is {app_version} in app.js but {sw_version} in sw.js — "
            f"the service worker would cache a runtime the app never asks for"
        )
    if not pinned("app.js", "PYODIDE_VERSION"):
        problems.append("app.js does not pin PYODIDE_VERSION")
    if not pinned("sw.js", "CACHE_VERSION"):
        problems.append("sw.js does not define CACHE_VERSION")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate every registered game.")
    parser.add_argument("game", nargs="*", help="game ids to check (default: all)")
    parser.add_argument("--fuzz", type=int, default=400, help="fuzz steps per game")
    args = parser.parse_args()

    print("\n  Checking Boo's Game Box\n")

    try:
        ids = engine.registered_ids()
    except Exception as exc:
        print(f"  ✗ games.json: {exc}\n")
        return 1

    if args.game:
        unknown = [g for g in args.game if g not in ids]
        if unknown:
            print(f"  ✗ not in games.json: {', '.join(unknown)}\n")
            return 1
        ids = args.game

    check_ids = len(ids) == len(set(ids))
    if not check_ids:
        print("  ✗ games.json lists the same game twice\n")
        return 1

    failed = 0
    for game_id in ids:
        ok, notes = check_game(game_id, args.fuzz)
        if ok:
            print(f"  ✓ {game_id}")
            for note in notes:
                print(f"      note: {note}")
        else:
            failed += 1
            print(f"  ✗ {game_id}")
            for note in notes:
                for line in str(note).splitlines():
                    print(f"      {line}")

    problems = [] if args.game else project_checks()
    if problems:
        print()
        for problem in problems:
            print(f"  ✗ {problem}")

    print()
    if failed or problems:
        if failed:
            print(f"  {failed} of {len(ids)} game(s) failed. Not deployable.\n")
        else:
            print("  The games are fine but the shell is not. Not deployable.\n")
        return 1
    print(f"  All {len(ids)} game(s) pass. Ready to deploy.")
    print("  Remember to bump CACHE_VERSION in public/sw.js.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
