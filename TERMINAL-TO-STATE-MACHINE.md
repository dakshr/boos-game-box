# Converting a Terminal Python App into a State Machine

A reusable procedure. Applies to any `input()`/`print()` loop that needs to run somewhere it can't block — a web page, a Telegram bot, a voice assistant, a test harness.

---

## The idea in one paragraph

A terminal program owns the clock. It decides when to ask, blocks until answered, prints, and loops. A browser, a bot, and a test runner all own the clock themselves — they call *you*, you answer, you return. So the conversion is a single inversion: stop pulling input, start receiving it. The loop becomes a function that takes the current state plus one input and returns the next state plus what to display. Everything else follows from that.

```
BEFORE                          AFTER
while True:                     def send(self, value) -> View:
    print(...)                      # update state from value
    x = input(...)                  # return what to show + what to ask
    # update state
```

---

## The contract

```python
class Game:
    def __init__(self, seed: int | None = None): ...
    def start(self) -> View: ...
    def send(self, value: str) -> View: ...
```

`View` carries two things: what to display, and what to ask next.

```python
@dataclass
class Choice:
    label: str      # shown to the user
    value: str      # returned to send()

@dataclass
class Prompt:
    kind: str       # "choice" | "number" | "text" | "continue" | "end"
    label: str = ""
    choices: list[Choice] = field(default_factory=list)
    min: int | None = None
    max: int | None = None

@dataclass
class View:
    lines: list[str]
    prompt: Prompt
    art: str | None = None
    sound: str | None = None
    score: int | None = None
```

Three properties make this work, and all three are worth defending:

- **`send()` is total.** Any string in, a valid `View` out. It never raises. Bad input returns a re-prompt.
- **State lives on the instance.** No module globals, no closures over mutable data. Two games can then run at once, and a test can construct one from scratch.
- **Randomness is injected.** `self.rng = random.Random(seed)`, never bare `random.*`. A seeded game replays identically, which is the only way to test one.

---

## Procedure

### Step 1 — Map the prompts

Before writing code, list every place the original calls `input()`. For each one, write down: what it asks, what it accepts, and what happens on invalid input. This list *is* your state enum. A five-prompt program has roughly five states.

If the same `input()` is inside a loop, it's one state that returns to itself — not five states.

### Step 2 — Name the states

Turn the list into a constant per state:

```python
ASK_NAME = "ask_name"
ASK_DIFFICULTY = "ask_difficulty"
PLAYING = "playing"
GAME_OVER = "game_over"
```

Strings, not an enum, if the states cross a JSON boundary later. `self.state` holds the current one.

### Step 3 — Hoist all state to `__init__`

Every local variable that survives across an `input()` call becomes `self.something`. Variables that live and die between two prompts stay local.

```python
def __init__(self, seed=None):
    self.rng = random.Random(seed)
    self.state = ASK_DIFFICULTY
    self.secret = None
    self.guesses = 0
    self.score = 0
```

### Step 4 — Replace `print()` with accumulation

Build a list instead of writing to a stream:

```python
def __init__(self, seed=None):
    ...
    self._lines = []

def say(self, text):
    self._lines.append(text)

def _flush(self, prompt, **kw) -> View:
    lines, self._lines = self._lines, []
    return View(lines=lines, prompt=prompt, **kw)
```

Now every `print(x)` becomes `self.say(x)`, and every point where the original would have blocked becomes `return self._flush(Prompt(...))`.

### Step 5 — Turn the loop into a dispatch

```python
def send(self, value: str) -> View:
    handler = getattr(self, f"_on_{self.state}", None)
    if handler is None:
        return self._error()
    return handler(value.strip())
```

Each handler does exactly what the body of the loop did between two `input()` calls: validate, update state, say things, return the next prompt.

### Step 6 — Write `start()`

`start()` is the code that ran *before* the first `input()`. It says the intro and returns the first prompt. It must be safe to call twice — calling it again should restart cleanly, because that's what the "Play again" button does.

### Step 7 — Verify against the original

Play both side by side with a fixed seed. Same wording, same rules, same edge cases, same win condition. If the wording drifted, fix the new one — the point of this refactor is that nothing about the experience changes.

---

## Worked example

**Before:**

```python
import random

def play():
    secret = random.randint(1, 20)
    tries = 0
    print("I'm thinking of a number between 1 and 20!")
    while True:
        guess = input("Your guess? ")
        if not guess.isdigit():
            print("Numbers only, please!")
            continue
        guess = int(guess)
        tries += 1
        if guess < secret:
            print("Too low!")
        elif guess > secret:
            print("Too high!")
        else:
            print(f"You got it in {tries} tries!")
            return
```

**After:**

```python
import random
from view import View, Prompt, Choice

ID = "number-hunt"
TITLE = "Number Hunt"
BLURB = "Guess the hidden number."
EMOJI = "🔢"
MIN_AGE = 5

GUESSING = "guessing"
DONE = "done"

class Game:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self._lines = []
        self.state = GUESSING
        self.secret = self.rng.randint(1, 20)
        self.tries = 0

    def say(self, text):
        self._lines.append(text)

    def _flush(self, prompt, **kw):
        lines, self._lines = self._lines, []
        return View(lines=lines, prompt=prompt, **kw)

    def start(self):
        self.__init__(self.rng.randint(0, 10**6))
        self.say("I'm thinking of a number between 1 and 20!")
        return self._ask()

    def _ask(self):
        return self._flush(
            Prompt(kind="number", label="Your guess?", min=1, max=20),
            score=self.tries,
        )

    def send(self, value):
        if self.state == DONE:
            return self.start()
        return self._on_guessing(value.strip())

    def _on_guessing(self, value):
        if not value.isdigit():
            self.say("Numbers only, please!")
            return self._ask()

        guess = int(value)
        self.tries += 1

        if guess < self.secret:
            self.say("Too low!")
            return self._ask()
        if guess > self.secret:
            self.say("Too high!")
            return self._ask()

        self.say(f"You got it in {self.tries} tries!")
        self.state = DONE
        return self._flush(
            Prompt(kind="end", label="Play again?"),
            sound="win",
            score=self.tries,
        )
```

Same wording, same rules. The only structural change: the loop turned inside out.

---

## Pattern reference

| Terminal pattern | State machine equivalent |
|---|---|
| `input("Press enter to continue")` | `Prompt(kind="continue")` |
| `time.sleep(2)` for pacing | `Prompt(kind="continue")`, or drop it entirely |
| `while True:` game loop | one state that returns to itself |
| Nested loop (round inside game) | outer counter on `self`, inner state |
| `input()` with menu of options | `Prompt(kind="choice", choices=[...])` |
| `if x not in valid: continue` | `self.say(msg)` then re-return the same prompt |
| `return` / `break` to end | set terminal state, return `Prompt(kind="end")` |
| `sys.exit()` | never — return an end view |
| `random.randint()` | `self.rng.randint()` |
| Reading/writing a score file | pass state in and out; let the caller persist it |
| `os.system("clear")` | return only the lines for this turn; the shell decides what to keep |
| ASCII banner via `print` | `View.art` |

---

## Anti-patterns

**Storing state in module globals.** It works for one player and breaks the moment there are two, or a test suite.

**Making `send()` raise on bad input.** The caller now needs error handling in two languages. Return a re-prompt instead.

**Returning a rendered string instead of a `View`.** You've just invented a terminal again, in a worse language. Return structured data and let the frontend decide how it looks.

**Leaving `random` unseeded.** Untestable, unreproducible, and impossible to debug a bug report.

**Fixing gameplay while refactoring.** If the original had a bug, port the bug, verify the port, then fix it as a separate change. Otherwise a behavior difference could be either the refactor or the fix, and you won't know which.

**Letting `start()` be non-idempotent.** "Play again" calls it. If it accumulates state, the second game is broken in a way that only shows up after someone's been playing for ten minutes.

---

## Checklist

- [ ] Zero `input()`, `print()`, `time.sleep()`, `sys.exit()` in the game module
- [ ] All persistent state on `self`, none at module level
- [ ] `random.Random(seed)` instance, no bare `random.*`
- [ ] `send()` handles `""`, `"abc"`, `"-1"`, `"999999999"`, emoji, and a 10,000-char string without raising
- [ ] `start()` called twice yields two identical fresh games
- [ ] Same seed produces the same sequence
- [ ] Terminal runner plays it identically to the original
- [ ] Standard library only
