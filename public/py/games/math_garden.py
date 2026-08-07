"""Math Garden — refactor of terminal-games/garden.py.

Same problems, same gentle second chance, same encouragement, same 3x3
garden, same closing report. The quit words still work when you play it in
a terminal; in the browser "Back to the box" does that job.

The garden grid travels in `View.art` so the shell can set it in a
monospaced font and keep the pipes lined up.
"""

import random

from view import View, Prompt, Choice

ID = "math-garden"
TITLE = "Math Garden"
BLURB = "Solve a little math, then plant your garden."
EMOJI = "🌱"
MIN_AGE = 5

ASK_NAME = "ask_name"
ASK_FIRST = "ask_first"
ASK_SECOND = "ask_second"
ASK_PLANT = "ask_plant"
ASK_WHERE = "ask_where"
ASK_MORE = "ask_more"
DONE = "done"

PLANTS = {
    "1": "🌼",  # flower
    "2": "🍓",  # strawberry
    "3": "🌳",  # tree
    "4": "🥕",  # carrot
}

PLANT_NAMES = {
    "1": "flower",
    "2": "strawberry",
    "3": "tree",
    "4": "carrot",
}

SIZE = 9  # 3x3 garden

RULE = "-" * 31

QUIT_FIRST = ("q", "quit", "exit", "bye")
QUIT_SECOND = ("q", "quit", "exit")


class Game:
    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed
        self._reset()

    # --- plumbing -------------------------------------------------------

    def say(self, text: str) -> None:
        self._lines.append(text)

    def _flush(self, prompt: Prompt, **kw) -> View:
        lines, self._lines = self._lines, []
        return View(lines=lines, prompt=prompt, **kw)

    def _reset(self) -> None:
        self.rng = random.Random(self._seed)
        self._lines: list[str] = []
        self.state = ASK_NAME
        self.garden = ["."] * SIZE
        self.solved = 0
        self.planted = 0
        self.name = ""
        self.question = ""
        self.hint = ""
        self.answer = 0
        self.pending_plant = ""

    # --- the game -------------------------------------------------------

    def start(self) -> View:
        self._reset()
        self.say("Welcome to the Calm Math Garden")
        self.say(RULE)
        self.say("Solve a little math, then choose what to plant.")
        self.say("No hurry. Take your time.")
        return self._flush(
            Prompt(kind="text", label="What is your name? (press Enter to skip)"),
            score=self.solved,
        )

    def send(self, value: str) -> View:
        if self.state == DONE:
            return self.start()
        handler = getattr(self, f"_on_{self.state}", None)
        if handler is None:  # pragma: no cover - unreachable while states match
            return self._finish()
        return handler(value.strip())

    # --- name -----------------------------------------------------------

    def _on_ask_name(self, value: str) -> View:
        self.name = value
        if self.name:
            self.say(f"Hello, {self.name}! Let's grow a garden together.")
        else:
            self.say("Let's grow a garden together.")
        return self._new_problem()

    # --- the maths ------------------------------------------------------

    def _make_problem(self):
        """Return (question_text, hint_text, answer) for a 5-6 year old."""
        kind = self.rng.choice(["add", "add", "sub", "sub", "count"])

        if kind == "add":
            a = self.rng.randint(1, 5)
            b = self.rng.randint(1, 5)
            # keep sum <= 10 for this age
            while a + b > 10:
                a = self.rng.randint(1, 5)
                b = self.rng.randint(1, 5)
            q = f"{a} + {b} = ?"
            hint = f"  hint: {'●' * a}  +  {'●' * b}  -> count all the dots"
            ans = a + b

        elif kind == "sub":
            a = self.rng.randint(3, 10)
            b = self.rng.randint(1, a - 1)
            # avoid 0 answer too often, keep it 1+
            if a - b == 0:
                b -= 1
            q = f"{a} - {b} = ?"
            hint = f"  hint: start at {a}, count back {b} -> {'●' * a} take away {'●' * b}"
            ans = a - b

        else:  # count - visual apples
            a = self.rng.randint(1, 4)
            b = self.rng.randint(1, 4)
            while a + b > 9:
                a = self.rng.randint(1, 4)
                b = self.rng.randint(1, 4)
            q = f"{'🍎' * a} + {'🍎' * b} = ?  (how many apples?)"
            hint = f"  hint: {a} apples and {b} more"
            ans = a + b

        return q, hint, ans

    def _new_problem(self) -> View:
        self.question, self.hint, self.answer = self._make_problem()
        self.state = ASK_FIRST
        self.say(f"--- Garden plot {self.planted + 1} of {SIZE} ---")
        self.say(f"Question: {self.question}")
        return self._flush(
            Prompt(kind="number", label="Your answer:"),
            score=self.solved,
        )

    def _on_ask_first(self, value: str) -> View:
        raw = value.lower()

        if raw in QUIT_FIRST:
            self.say("")
            self.say("You can come back anytime. Your garden will wait.")
            return self._finish()

        # allow empty
        if raw == "":
            self.say("Try typing a number. You can do it.")
            return self._new_problem()

        # check numeric
        try:
            given = int(raw)
        except ValueError:
            self.say("Please type a number, like 5 or 7.")
            return self._new_problem()

        if given == self.answer:
            self.say("Correct! Nice counting.")
            self.say("")
            self.solved += 1
            return self._offer_seed(sound="correct")

        # gentle second chance with hint
        self.say(f"Not quite. {self.hint}")
        self.say(f"Try once more. What is {self.question}")
        self.state = ASK_SECOND
        return self._flush(
            Prompt(kind="number", label="Your answer:"),
            score=self.solved,
            sound="wrong",
        )

    def _on_ask_second(self, value: str) -> View:
        if value in QUIT_SECOND:
            self.say("")
            self.say("Pausing here. Bye for now.")
            return self._finish()

        try:
            given2 = int(value)
        except ValueError:
            given2 = None

        if given2 == self.answer:
            self.say("You got it on the second try. Good persistence.")
            self.say("")
            self.solved += 1
            return self._offer_seed(sound="correct")

        self.say(
            f"The answer was {self.answer}. Good try — counting is hard and you kept going."
        )
        self.say("")
        # still let them plant to keep it encouraging
        return self._offer_seed()

    # --- planting -------------------------------------------------------

    def _draw_garden(self) -> str:
        rows = ["Your garden (1-9):", "+----+----+----+"]
        for r in range(3):
            row = self.garden[r * 3 : (r + 1) * 3]
            # numbers for empty plots, emoji for planted — both 4 visual
            # columns so the pipes line up
            cells = []
            for i, cell in enumerate(row):
                idx = r * 3 + i + 1
                if cell == ".":
                    cells.append(f" {idx}  ")
                else:
                    cells.append(f" {cell} ")
            rows.append("|" + "|".join(cells) + "|")
            rows.append("+----+----+----+")
        return "\n".join(rows)

    def _offer_seed(self, **kw) -> View:
        self.state = ASK_PLANT
        return self._flush(
            Prompt(
                kind="choice",
                label="You earned a seed! What would you like to plant?",
                choices=[
                    Choice(f"{PLANTS[k]}  {PLANT_NAMES[k]}", k) for k in sorted(PLANTS)
                ],
            ),
            art=self._draw_garden(),
            score=self.solved,
            **kw,
        )

    def _empty_plots(self) -> list[str]:
        return [str(i + 1) for i, v in enumerate(self.garden) if v == "."]

    def _on_ask_plant(self, value: str) -> View:
        if value not in PLANTS:
            self.say("Pick 1, 2, 3, or 4.")
            return self._offer_seed()

        self.pending_plant = value
        return self._ask_where()

    def _ask_where(self, **kw) -> View:
        empty = self._empty_plots()
        self.state = ASK_WHERE
        self.say(f"Where should it grow? Empty plots: {', '.join(empty)}")
        return self._flush(
            Prompt(
                kind="choice",
                label="Pick plot number:",
                choices=[Choice(plot, plot) for plot in empty],
            ),
            score=self.solved,
            **kw,
        )

    def _on_ask_where(self, value: str) -> View:
        empty = self._empty_plots()
        if value not in empty:
            self.say(f"Choose an empty plot from: {', '.join(empty)}")
            return self._ask_where()

        choice = self.pending_plant
        self.garden[int(value) - 1] = PLANTS[choice]
        self.planted += 1
        self.say(f"Planted a {PLANT_NAMES[choice]} {PLANTS[choice]} in plot {value}.")

        if self.planted >= SIZE:
            return self._finish()

        self.state = ASK_MORE
        return self._flush(
            Prompt(
                kind="choice",
                label="Keep planting?",
                choices=[Choice("Keep planting", ""), Choice("Stop for now", "q")],
            ),
            art=self._draw_garden(),
            score=self.solved,
        )

    def _on_ask_more(self, value: str) -> View:
        if value.lower() == "q":
            return self._finish()
        return self._new_problem()

    # --- closing --------------------------------------------------------

    def _finish(self) -> View:
        self.say("")
        self.say(RULE)
        self.say(
            f"Finished! You solved {self.solved} problem(s) "
            f"and planted {self.planted} seed(s)."
        )
        if self.planted == SIZE:
            self.say("Your garden is full. You built it with math and choices.")
        else:
            self.say("Come back to finish your garden whenever you like.")
        self.say("Bye, gardener!")
        self.state = DONE
        return self._flush(
            Prompt(kind="end", label="Plant another garden?"),
            art=self._draw_garden(),
            score=self.solved,
            sound="win" if self.planted == SIZE else None,
        )
