# Boo's Game Box

A little box of Python games that runs in a browser, installs to a home
screen, and keeps working with the wifi off.

No backend. No build step. No npm. The folder that is written is the
folder that is deployed.

---

## What it is

Four Python games that used to be terminal scripts now run inside the
browser through [Pyodide](https://pyodide.org) (CPython compiled to
WebAssembly). The game logic is still plain Python — you can open
`public/py/games/secret_number.py` in an editor, change a line, refresh,
and see it.

The games themselves have no idea a browser exists. Each one is a state
machine: it is handed one string and returns one `View` describing what to
show and what to ask next. That is why the same file plays in a terminal,
in a test harness, and on an iPad.

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

## Layout

```
boos-game-box/
├── terminal-games/          ORIGINALS — reference only, never modified
├── public/                  everything here is deployed verbatim
│   ├── index.html
│   ├── styles.css
│   ├── app.js               boots Pyodide, renders Views, posts answers back
│   ├── sw.js                offline cache — HAS A VERSION NUMBER, BUMP IT
│   ├── manifest.json
│   ├── icons/
│   └── py/
│       ├── engine.py        loader + event router
│       ├── view.py          the View / Prompt contract
│       ├── games.json       THE REGISTRY — add a game by editing this
│       └── games/
├── tools/
│   ├── run_terminal.py      play any game in a terminal
│   ├── check_games.py       pre-deploy gate
│   └── make_icons.py        regenerates the three PNG icons
├── ADDING-A-GAME.md
└── README.md
```

---

## Running it locally

Any static file server will do. From the repository root:

```bash
python -m http.server 8000 --directory public
```

Then open <http://localhost:8000>.

The service worker deliberately **does not register on localhost**, so
editing a `.py` file and refreshing shows the change immediately with no
cache in the way. To test the real offline behaviour locally, open
<http://localhost:8000/?sw=1> instead.

Playing a game without a browser at all:

```bash
python tools/run_terminal.py
```

```bash
python tools/run_terminal.py math-garden --seed 3
```

Checking everything before a deploy:

```bash
python tools/check_games.py
```

---

## Deploying to Cloudflare Pages

Both paths use `public/` as the output directory and **no build command**.

### Direct upload

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** →
   **Upload assets**.
2. Name the project (e.g. `boos-game-box`).
3. Drag the **`public/`** folder in — the folder itself, not the repo root.
4. **Deploy site.**

To update: **Create a new deployment** and drag `public/` in again.

### Git connection

1. Push this repository to GitHub or GitLab.
2. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** →
   **Connect to Git**.
3. Pick the repository, then set:

   | Setting                | Value    |
   |------------------------|----------|
   | Framework preset       | None     |
   | Build command          | *(leave empty)* |
   | Build output directory | `public` |

4. **Save and Deploy.** Every push to the production branch redeploys.

### Before every deploy

1. `python tools/check_games.py` — must pass clean.
2. **Bump `CACHE_VERSION` in `public/sw.js`.**

```js
const CACHE_VERSION = "v4";   //  ← this one
```

The worker is cache-first, which is what makes the app work on a plane. It
also means a device that has already visited will keep serving the old
files until this number changes. A stale service worker shipping
yesterday's game is the single most common way this app breaks. When the
number changes, the new worker deletes every cache that doesn't match and
takes over on the next launch.

---

## Pinned versions

| Thing   | Version    | Where                                    |
|---------|------------|------------------------------------------|
| Pyodide | `314.0.3`  | `PYODIDE_VERSION` in `app.js` **and** `sw.js` |

Pyodide is pinned rather than tracking `latest` on purpose: a new Pyodide
is a new CPython, and a new CPython can quietly change how a game behaves.
Bump it deliberately, then replay every game against its original in
`terminal-games/`.

The two constants must agree — `check_games.py` fails if they drift, since
the service worker would otherwise cache a runtime the app never asks for.
Pyodide 314.0.3 is CPython 3.14. Current releases are listed at
<https://cdn.jsdelivr.net/pyodide/>.

---

## Installing on a device

**Android / Chrome / Edge** — the browser offers "Install app" or "Add to
Home screen" by itself once the manifest and service worker are live.

**iPhone / iPad** — Safari has no install prompt. Tap **Share**, then
**Add to Home Screen**. The app shows this as a small dismissible line on
the picker screen when it detects iOS outside standalone mode.

Either way it opens fullscreen, portrait, with no browser chrome, and the
second launch needs no network at all.

---

## Adding a game

See [ADDING-A-GAME.md](ADDING-A-GAME.md). It is one new file, one new line
in `public/py/games.json`, and a cache bump. Nothing in `app.js` or
`engine.py` needs to change, ever.

---

## The games

| Game | Original | Notes |
|---|---|---|
| Secret Number | `guessing_game.py` | Guess 1–20 with high/low hints. |
| Silly Story | `mad_libs.py` | Tap silly words, get one of eight stories. **Redesigned — see below.** |
| Magic Zoo | `magic_zoo.py` | Pick an animal, collect stars, party every fifth. |
| Math Garden | `garden.py` | Solve a sum, plant a 3×3 garden. |

### Three of them are faithful ports

Secret Number, Magic Zoo and Math Garden were verified line by line against
the seeded originals. The handful of places where they could not be identical:

- **Bad input no longer crashes.** `guessing_game.py` did `int(input(...))`
  and raised a `ValueError` on `"abc"`. The contract forbids `send()` from
  raising, so it re-prompts instead.
- **ANSI colour and `time.sleep()` are gone from Magic Zoo.** The shell
  paints the screen now, and the bouncing animals still print — all at
  once instead of a fifth of a second apart.
- **Magic Zoo's banner closes properly.** The original's middle line was one
  column short of its own borders; the colour codes hid it.
- **Magic Zoo's menu and Math Garden's plant/plot choices are buttons.**
  The values behind them (`"1"`…`"6"`, `"0"`, `"q"`) are exactly the
  strings the originals accepted, which is why they still work in a
  terminal.
- **The garden grid is drawn above its caption, not below.** A `View`
  carries one piece of art, and it renders after that turn's lines.

For those three, rules, wording, difficulty and win conditions are unchanged.
If something reads differently from the original, that's a bug — the
originals in `terminal-games/` are the reference and are never modified.

### Silly Story is a deliberate redesign

`mad_libs.py` asked six typed questions and told the same six sentences every
time. Faithful, and stale after one go. It was rebuilt around two changes:

- **Words are chosen from picture buttons**, five sampled fresh from a bank
  each time, with `✏️ My own word` always available. A child who cannot type
  can play the whole game; anyone can still type any word they like, which is
  why it still works in a terminal.
- **Eight stories instead of one**, each asking only the words it needs, and
  a **"Same words, new story"** button that re-runs what the child already
  picked through a different template. Words accumulate, so the second remix
  usually asks for nothing at all.

The original story is still in there as the first of the eight, word for word,
and `terminal-games/mad_libs.py` is untouched. Adding a ninth story means
appending one dict to `STORIES` in
[`public/py/games/silly_story.py`](public/py/games/silly_story.py) — the
state machine reads the slot list off whichever story it picked.

---

## Regenerating the icons

The three PNGs are drawn by a script rather than checked in as opaque
binaries. If you change the palette:

```bash
python tools/make_icons.py
```

It uses only the standard library — no Pillow, no design tool.
