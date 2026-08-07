# Boo's Game Box — Build Spec

**For:** Claude Code
**Deliverable:** A static, installable web app that runs existing Python games in the browser via Pyodide, hosted on Cloudflare Pages.
**Audience:** Children roughly ages 4–8, on tablets and laptops.

---

## 0. Context

There are currently 4 Python games in a folder called `terminal-games/`. Each is a standalone `.py` file written for the terminal: it uses `input()` to read and `print()` to write, and it drives itself with a `while` loop.

That structure cannot run in a browser. `input()` blocks the thread; a web UI is event-driven. The core of this work is removing blocking I/O from the game logic, then wrapping the result in a browser shell.

**Do not rewrite the games' rules, difficulty, wording, or feel.** Behavior must be preserved exactly. This is a refactor of I/O, not a redesign of gameplay.

---

## 1. Non-negotiable requirements

1. **Adding a fifth game must take one file and one line.** Drop a new `.py` into the games folder, add its ID to a manifest, done. No touching the engine, no touching the frontend, no build step.
2. **No backend.** Static files only. No server, no database, no per-user state on any machine but the child's.
3. **No build step.** No npm, no bundler, no transpiler. The folder that is written is the folder that is deployed. A person should be able to edit a `.py` file, refresh, and see the change.
4. **Works offline after first load**, including on an iPad in airplane mode.
5. **Every game must remain playable in a terminal** after the refactor, via a provided runner. This is the regression test.
6. **Tap-first.** A four-year-old cannot reliably type. Where a game asks for one of a fixed set of answers, the UI must render buttons, not a text field.

---

## 2. Target architecture

```
Browser (child's device)
  │
  ├── index.html ── styles.css ── app.js        ← shell: renders views, sends events
  │                                   │
  │                                   ▼
  ├── Pyodide (WebAssembly)      engine.py      ← loads game modules, routes events
  │                                   │
  │                                   ▼
  │                              games/*.py     ← pure state machines, no I/O
  │
  └── sw.js + manifest.json                     ← offline cache + home-screen install
```

Everything runs on the device. Pyodide is fetched from a CDN on first load, then cached by the service worker.

---

## 3. Repository layout

Create this structure. Keep `terminal-games/` untouched as the reference implementation.

```
boos-game-box/
├── terminal-games/              # ORIGINALS — read-only reference, do not modify
│   ├── game_one.py
│   └── ...
├── public/                      # everything here is deployed verbatim
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── sw.js
│   ├── manifest.json
│   ├── icons/
│   │   ├── icon-192.png
│   │   ├── icon-512.png
│   │   └── icon-maskable-512.png
│   └── py/
│       ├── engine.py            # loader + event router
│       ├── view.py              # the View / Prompt contract
│       ├── games.json           # THE REGISTRY — add a game by editing this
│       └── games/
│           ├── __init__.py
│           ├── game_one.py
│           └── ...
├── tools/
│   ├── run_terminal.py          # play any refactored game in the terminal
│   └── check_games.py           # validates every game against the contract
├── ADDING-A-GAME.md
└── README.md
```

---

## 4. The state machine contract

This is the heart of the spec. Every game must conform to it.

### 4.1 `view.py`

```python
from dataclasses import dataclass, field
from typing import Literal, Optional

@dataclass
class Choice:
    label: str                  # what the child sees on the button
    value: str                  # what gets sent back to the game

@dataclass
class Prompt:
    kind: Literal["choice", "number", "text", "continue", "end"]
    label: str = ""             # e.g. "Pick a color"
    choices: list[Choice] = field(default_factory=list)   # kind == "choice"
    min: Optional[int] = None   # kind == "number"
    max: Optional[int] = None

@dataclass
class View:
    lines: list[str]            # what to display, newest last
    prompt: Prompt
    art: Optional[str] = None   # optional emoji/ASCII banner
    sound: Optional[str] = None # "correct" | "wrong" | "win" — shell may ignore
    score: Optional[int] = None
```

`kind="continue"` renders a single "Next" button — use it for pacing, where the terminal version had a `input("Press enter...")` or a `time.sleep()`.
`kind="end"` renders a "Play again" / "Back to the box" pair and marks the game over.

### 4.2 Every game module exposes

```python
ID = "counting-caterpillar"     # kebab-case, must match games.json
TITLE = "Counting Caterpillar"
BLURB = "Count the leaves and feed the caterpillar."
EMOJI = "🐛"
MIN_AGE = 4

class Game:
    def __init__(self, seed: int | None = None) -> None:
        """Set up initial state. Seed the RNG from `seed` if given —
        never call the global random module directly."""

    def start(self) -> View:
        """Return the opening view. Must not mutate anything a second
        call would depend on; calling start() again restarts cleanly."""

    def send(self, value: str) -> View:
        """Handle one input. `value` is always a string — cast inside.
        Must never raise on bad input; return a View that re-prompts."""
```

### 4.3 Hard rules for game modules

- No `input()`, no `print()`, no `time.sleep()`, no `os`, no `sys.exit()`.
- No module-level mutable state. All state lives on the instance.
- Use `self.rng = random.Random(seed)` — never bare `random.randint()`. Seeding is what makes games testable.
- `send()` is total: any string in, a valid `View` out. Bad input re-prompts with a gentle message in the game's own voice.
- Pure Python standard library only. No third-party imports — Pyodide would need to fetch wheels, which breaks the no-build-step rule.

---

## 5. Build phases

### Phase 1 — Refactor the 4 games

For each file in `terminal-games/`, produce a conforming module in `public/py/games/`.

Follow the procedure in `TERMINAL-TO-STATE-MACHINE.md` (the companion document). Work one game at a time and fully finish each — including terminal verification — before starting the next.

**Verification for each game:** run it through `tools/run_terminal.py` and play it side by side with the original. Same prompts, same wording, same rules, same win conditions. Where the original used a fixed set of answers, those become `Choice` buttons; the underlying accepted values stay identical.

### Phase 2 — Engine and registry

`public/py/games.json` is the single place a game is registered:

```json
{
  "games": ["counting-caterpillar", "color-quest", "word-wiggle", "star-catcher"]
}
```

Each string is both the module filename (`counting_caterpillar.py`, underscored) and the `ID` inside it. Enforce that mapping in the loader and fail loudly on mismatch.

`engine.py` responsibilities:
- Read `games.json`, import each module, read its metadata, expose a catalog to JS.
- Instantiate a game on request, hold the live instance, route `send()` calls.
- Serialize `View` objects to plain dicts for the JS bridge.
- Catch any exception from game code and return a friendly error view rather than crashing the page.

`tools/check_games.py` validates every registered game: module imports, required constants present, `Game` class conforms, `start()` returns a `View`, `send()` survives a fuzz of junk strings without raising. This is the pre-deploy gate.

### Phase 3 — HTML shell

**The screen the child sees.** Two states: the box (game picker) and a game.

Design direction — follow this exactly:

- **Palette:** cream `#FDF6E3` ground, deep teal `#2A9D8F` primary, warm coral `#E76F51` for wrong/retry, mustard `#E9C46A` for rewards, ink `#264653` for text.
- **Type:** Fraunces for titles and game names (heavy optical size, it has personality at large sizes); Plus Jakarta Sans for everything a child reads as instruction. Both from Google Fonts, loaded with `display=swap`, and cached by the service worker.
- **Signature element:** the picker is an actual *box* — game tiles sit as chunky cards with a 4px offset drop shadow, no blur, slightly rotated at rest (±1.5°), snapping straight on hover/tap. It should feel like picking up a physical card, not clicking a menu item.
- **Touch targets minimum 64px.** Buttons are large, high-contrast, and spaced so a small hand doesn't hit two.
- Restraint everywhere else: one accent per screen, no gradients, no scattered animation. Respect `prefers-reduced-motion`.

**Behavior:**
- A loading screen while Pyodide boots (this is 1–3 seconds on first load). Not a spinner — a progress line with plain words: "Waking up the games…". Never leave the child on a blank screen.
- Game view renders `view.lines` in a scrolling transcript, `view.prompt` as the input control beneath it, `view.score` as a persistent badge if present.
- A "Back to the box" control always visible, no confirmation dialog.
- Keyboard accessible: buttons reachable by Tab, visible focus ring, Enter activates.
- No text input at all unless `prompt.kind` is `"text"` or `"number"`. Number prompts get a numeric keypad (`inputmode="numeric"`).

### Phase 4 — PWA

- `manifest.json`: name "Boo's Game Box", short name "Game Box", `display: "standalone"`, `background_color: "#FDF6E3"`, `theme_color: "#2A9D8F"`, `orientation: "portrait"`, all three icons wired including the maskable variant.
- `sw.js`: cache-first for the app shell, Pyodide runtime, fonts, and all `py/` files. **Version the cache name as a constant at the top of the file** and document that it must be bumped on every deploy — a stale service worker serving an old game is the single most common failure mode here.
- Include an update path: on activation, delete caches that don't match the current version, then `clients.claim()`.
- Register the service worker from `index.html`. Guard it behind a `"serviceWorker" in navigator` check.
- iOS does not offer an install prompt. Add a small, dismissible line on the picker screen for Safari users: "Tap Share, then Add to Home Screen." Detect iOS + non-standalone before showing it.

### Phase 5 — Deploy

Cloudflare Pages, direct upload or Git connection, with `public/` as the output directory and no build command. Document both paths in `README.md`, including how to bump the cache version before pushing.

Pin the Pyodide version explicitly in `app.js` rather than tracking `latest` — check the current stable release on the Pyodide CDN when wiring this up, and note the pinned version in `README.md` so it can be bumped deliberately.

---

## 6. Adding a game later (write this up as `ADDING-A-GAME.md`)

The document must make this a four-step task:

1. Write `public/py/games/my_game.py` following the contract in §4.
2. Add `"my-game"` to the array in `public/py/games.json`.
3. Run `python tools/check_games.py` and `python tools/run_terminal.py my-game`.
4. Bump `CACHE_VERSION` in `sw.js`, deploy.

Include a complete, copy-pasteable skeleton game in that document. Someone should be able to make a new game by editing the skeleton without reading anything else.

---

## 7. Acceptance criteria

- [ ] All 4 games play identically to their `terminal-games/` originals, verified side by side.
- [ ] `python tools/check_games.py` passes clean.
- [ ] `python tools/run_terminal.py <id>` plays any game in a terminal.
- [ ] The picker loads on a phone, a tablet, and a desktop browser without layout breakage.
- [ ] Pyodide boot shows progress, never a blank screen.
- [ ] Installs to home screen on Android (prompt) and iOS (documented manual path).
- [ ] Second load works fully offline with wifi disabled.
- [ ] Bumping `CACHE_VERSION` and redeploying delivers changed game code on next launch.
- [ ] Adding a fifth game requires editing exactly two files, neither of which is `app.js` or `engine.py`. Prove this by building a trivial fifth game, confirming it appears, then removing it.
- [ ] Every interactive control is reachable by keyboard with a visible focus state.
- [ ] Nothing in `games/` imports outside the standard library.

---

## 8. Order of work

Do not build the frontend first. The order matters because the contract is what everything else depends on:

1. `view.py` and one refactored game + `run_terminal.py` — prove the contract works in a terminal.
2. The remaining three games.
3. `check_games.py`.
4. `engine.py` + a deliberately ugly HTML page that just proves Pyodide can play a game.
5. Only then, the real shell and styling.
6. PWA.
7. Deploy docs.

Stop and report after step 1. The contract is worth confirming before it is applied four times.
