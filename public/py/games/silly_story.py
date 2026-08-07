"""Silly Story — refactor of terminal-games/mad_libs.py.

Same six questions in the same order, same story, same wording.

Two behavioural notes:
  * An empty answer re-prompts instead of leaving a hole in the story.
  * "Want to make another story?" actually makes another one here, because
    it can — the original could only tell you to re-run the script.
"""

from view import View, Prompt, Choice

ID = "silly-story"
TITLE = "Silly Story"
BLURB = "Give me some words and I'll make a silly story."
EMOJI = "📖"
MIN_AGE = 6

COLLECTING = "collecting"
ASK_AGAIN = "ask_again"
DONE = "done"

RULE = "-" * 30

# (slot, prompt label, prompt kind) in the order the original asks them.
QUESTIONS = [
    ("name", "Give me a kid's name:", "text"),
    ("animal", "Name an animal:", "text"),
    ("color", "Name a color:", "text"),
    ("food", "Name a yummy food:", "text"),
    ("number", "Give me a number:", "number"),
    ("silly_sound", "Make a silly sound (like 'boing' or 'wheee'):", "text"),
]


class Game:
    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed  # this game has no randomness; kept for the contract
        self._reset()

    # --- plumbing -------------------------------------------------------

    def say(self, text: str) -> None:
        self._lines.append(text)

    def _flush(self, prompt: Prompt, **kw) -> View:
        lines, self._lines = self._lines, []
        return View(lines=lines, prompt=prompt, **kw)

    def _reset(self) -> None:
        self._lines: list[str] = []
        self.state = COLLECTING
        self.step = 0
        self.words: dict[str, str] = {}

    # --- the game -------------------------------------------------------

    def start(self) -> View:
        self._reset()
        self.say("Let's make a SILLY story together!")
        self.say("I'll ask you for some words, then watch the magic happen...")
        return self._ask()

    def _ask(self) -> View:
        _slot, label, kind = QUESTIONS[self.step]
        return self._flush(Prompt(kind=kind, label=label))

    def send(self, value: str) -> View:
        if self.state == DONE:
            return self.start()
        if self.state == ASK_AGAIN:
            return self._on_ask_again(value.strip().lower())
        return self._on_collecting(value.strip())

    def _on_collecting(self, value: str) -> View:
        if not value:
            self.say("I didn't catch that one — give me a word!")
            return self._ask()

        slot, _label, _kind = QUESTIONS[self.step]
        self.words[slot] = value
        self.step += 1

        if self.step < len(QUESTIONS):
            return self._ask()
        return self._tell_story()

    def _tell_story(self) -> View:
        w = self.words
        name, animal = w["name"], w["animal"]
        color, food = w["color"], w["food"]
        number, silly_sound = w["number"], w["silly_sound"]

        self.say("")
        self.say("Here is your story...")
        self.say(RULE)
        self.say(f"Once upon a time, {name} found a {color} {animal} in the backyard!")
        self.say(f'The {animal} said, "{silly_sound}!" and did a little dance.')
        self.say(f"{name} was so surprised that they dropped their {food}.")
        self.say(f"Then {number} more {animal}s showed up, all wearing tiny hats!")
        self.say(f"Everyone laughed and had a {color} {food} party until bedtime.")
        self.say("THE END!")
        self.say(RULE)

        self.state = ASK_AGAIN
        return self._flush(
            Prompt(
                kind="choice",
                label="Want to make another story?",
                choices=[Choice("Yes!", "yes"), Choice("No thanks", "no")],
            ),
            sound="win",
        )

    def _on_ask_again(self, value: str) -> View:
        if value.startswith("y"):
            view = self.start()
            return View(
                lines=["Yay! Here comes a brand new silly story!"] + view.lines,
                prompt=view.prompt,
                art=view.art,
                sound=view.sound,
                score=view.score,
            )

        self.say("Thanks for playing! Bye bye!")
        self.state = DONE
        return self._flush(Prompt(kind="end", label="Another story?"))
