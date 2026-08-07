"""Secret Number — refactor of terminal-games/guessing_game.py.

Same wording, same rules, same tier messages. The only behavioural change
is that non-numeric input re-prompts instead of crashing with a ValueError
(the contract forbids raising from send()).
"""

import random

from view import View, Prompt

ID = "secret-number"
TITLE = "Secret Number"
BLURB = "I'm thinking of a number. Can you find it?"
EMOJI = "🔢"
MIN_AGE = 5

GUESSING = "guessing"
DONE = "done"

LOW = 1
HIGH = 20


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
        """Back to a brand new game. A fixed seed replays exactly; no seed
        means Random() draws fresh entropy, so 'play again' is a new number."""
        self.rng = random.Random(self._seed)
        self._lines: list[str] = []
        self.state = GUESSING
        self.secret = self.rng.randint(LOW, HIGH)
        self.tries = 0

    # --- the game -------------------------------------------------------

    def start(self) -> View:
        self._reset()
        self.say("Welcome to the Secret Number Game!")
        self.say(f"I'm thinking of a number between {LOW} and {HIGH}...")
        return self._ask()

    def _ask(self, **kw) -> View:
        return self._flush(
            Prompt(kind="number", label="What's your guess?", min=LOW, max=HIGH),
            score=self.tries,
            **kw,
        )

    def send(self, value: str) -> View:
        if self.state == DONE:
            return self.start()
        return self._on_guessing(value.strip())

    def _on_guessing(self, value: str) -> View:
        try:
            guess = int(value)
        except ValueError:
            self.say("Numbers only, please! Try one between 1 and 20.")
            return self._ask()

        self.tries += 1

        if guess < self.secret:
            self.say("Too low! Try a bigger number.")
            return self._ask(sound="wrong")
        if guess > self.secret:
            self.say("Too high! Try a smaller number.")
            return self._ask(sound="wrong")

        self.say(f"YOU GOT IT! The number was {self.secret}!")
        self.say(f"You found it in {self.tries} tries!")

        if self.tries <= 3:
            self.say("WOW! You're a guessing SUPERSTAR!")
        elif self.tries <= 6:
            self.say("Great job, you smart cookie!")
        else:
            self.say("You did it! Practice makes perfect!")

        self.state = DONE
        return self._flush(
            Prompt(kind="end", label="Play again?"),
            sound="win",
            score=self.tries,
        )
