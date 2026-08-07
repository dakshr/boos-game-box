# Adding a game

Four steps. You do not need to touch `app.js`, `engine.py`, `styles.css`,
or `index.html` — ever.

---

## 1. Write the game

Copy the skeleton at the bottom of this file to
`public/py/games/my_game.py`. Change the name, change the questions, done.

The filename is the game's ID with hyphens turned into underscores:

| ID in `games.json` | filename                 |
|--------------------|--------------------------|
| `my-game`          | `games/my_game.py`       |
| `counting-bears`   | `games/counting_bears.py`|

They have to match. The loader checks, and refuses to start if they don't.

## 2. Register it

Add the ID to `public/py/games.json`:

```json
{
  "games": ["secret-number", "silly-story", "magic-zoo", "math-garden", "my-game"]
}
```

That is the whole registration. The picker, the service worker, and the
Python loader all read this file.

## 3. Check it, then play it

```bash
python tools/check_games.py
```

```bash
python tools/run_terminal.py my-game
```

`check_games.py` imports the module, checks its metadata, plays it with a
fixed seed twice to be sure it is deterministic, and then throws several
hundred pieces of junk at `send()` to be sure it never raises. It has to
pass before you deploy.

`run_terminal.py` lets you actually play it, in a terminal, with no
browser and no Pyodide involved. Add `--seed 1` to get the same game every
time while you are working on it.

## 4. Bump the cache and deploy

Open `public/sw.js` and increase `CACHE_VERSION` by one:

```js
const CACHE_VERSION = "v4";
```

**This is not optional.** The service worker is cache-first. Any device
that has opened the app before will keep serving the old files until this
number changes.

Then deploy `public/` (see [README.md](README.md)).

---

## The contract, in one page

Your module must expose five constants and a `Game` class:

```python
ID = "my-game"          # kebab-case, matches games.json and the filename
TITLE = "My Game"       # up to 24 characters — it goes on a card
BLURB = "One line."     # up to 80 characters
EMOJI = "🎲"
MIN_AGE = 4

class Game:
    def __init__(self, seed: int | None = None): ...
    def start(self) -> View: ...
    def send(self, value: str) -> View: ...
```

A `View` says two things: what to show, and what to ask next.

```python
View(
    lines=["Hello!"],           # what to display, newest last
    prompt=Prompt(...),         # what to ask
    art="🌼🌼🌼",                # optional; shown in a monospaced box
    sound="correct",            # optional: "correct" | "wrong" | "win"
    score=3,                    # optional; shown as a badge
)
```

A `Prompt` is one of five kinds:

| kind         | what the child sees                        | what `send()` gets      |
|--------------|--------------------------------------------|-------------------------|
| `"choice"`   | one big button per `Choice`                | that choice's `value`   |
| `"number"`   | a numeric keypad and a Go button           | whatever was typed      |
| `"text"`     | a text box and a Go button                 | whatever was typed      |
| `"continue"` | a single "Next" button                     | `""`                    |
| `"end"`      | "Play again" and "Back to the box"         | nothing; the game is over |

**Prefer `choice`.** A four-year-old cannot reliably type. If your game
accepts one of a fixed set of answers, it must be buttons.

### The rules that are actually enforced

`check_games.py` will fail you for any of these:

- calling `input()`, `print()`, `open()`, `exit()`, `eval()`, or `exec()`
- importing `os`, `sys`, `time`, `subprocess`, or anything outside the
  standard library
- calling `random.randint()` and friends directly — use
  `self.rng = random.Random(seed)` and then `self.rng.randint(...)`
- a lowercase variable at module level (all per-player state lives on the
  instance, so two children can play at once and a test can build one from
  scratch)
- `send()` raising on any input at all
- a `"choice"` prompt with no choices, which would be a dead end
- `start()` not being repeatable — "Play again" calls it

### Why `send()` must never raise

The child is on a tablet, on their own, and there is nobody to read the
error message to them. Bad input gets a gentle re-prompt in the game's own
voice:

```python
if not value.isdigit():
    self.say("Numbers only, please!")
    return self._ask()
```

---

## Copy-paste skeleton

Save as `public/py/games/my_game.py` and start editing.

```python
"""My Game — a short description of what it is."""

import random

from view import View, Prompt, Choice

ID = "my-game"
TITLE = "My Game"
BLURB = "One short line for the card."
EMOJI = "🎲"
MIN_AGE = 4

# One constant per state. `self.state` holds the current one, and `send()`
# dispatches to the matching `_on_<state>` method.
ASKING = "asking"
DONE = "done"


class Game:
    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed
        self._reset()

    # --- plumbing you can leave exactly as it is -------------------------

    def _reset(self) -> None:
        """Everything that makes a fresh game. Called by __init__ and by
        start(), so 'Play again' always hands back a clean one."""
        self.rng = random.Random(self._seed)
        self._lines: list[str] = []
        self.state = ASKING
        # --- your state goes here ---
        self.secret = self.rng.choice(["red", "blue", "green"])
        self.tries = 0

    def say(self, text: str) -> None:
        """Instead of print()."""
        self._lines.append(text)

    def _flush(self, prompt: Prompt, **kw) -> View:
        """Hand over everything said since the last turn, plus the question."""
        lines, self._lines = self._lines, []
        return View(lines=lines, prompt=prompt, **kw)

    def send(self, value: str) -> View:
        if self.state == DONE:
            return self.start()
        handler = getattr(self, f"_on_{self.state}", None)
        if handler is None:
            return self.start()
        return handler(value.strip())

    # --- the game ---------------------------------------------------------

    def start(self) -> View:
        """Whatever the terminal version printed before the first input()."""
        self._reset()
        self.say("I'm thinking of a colour!")
        return self._ask()

    def _ask(self, **kw) -> View:
        return self._flush(
            Prompt(
                kind="choice",
                label="Which one?",
                choices=[
                    Choice("🔴 Red", "red"),
                    Choice("🔵 Blue", "blue"),
                    Choice("🟢 Green", "green"),
                ],
            ),
            score=self.tries,
            **kw,
        )

    def _on_asking(self, value: str) -> View:
        # send() is total: anything can arrive here, including "" and emoji.
        if value not in ("red", "blue", "green"):
            self.say("Pick one of the colours!")
            return self._ask()

        self.tries += 1

        if value != self.secret:
            self.say("Not that one. Try again!")
            return self._ask(sound="wrong")

        self.say(f"Yes! It was {self.secret}!")
        self.say(f"You found it in {self.tries} goes.")
        self.state = DONE
        return self._flush(
            Prompt(kind="end", label="Play again?"),
            sound="win",
            score=self.tries,
        )
```

Then:

```bash
python tools/check_games.py my-game
```
