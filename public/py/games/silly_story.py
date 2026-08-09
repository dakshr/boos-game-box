"""Silly Story — a mad-libs game for people who cannot type yet.

Grown out of terminal-games/mad_libs.py, and the one game in the box that is
deliberately *not* a faithful port. The original asked six typed questions and
told the same six sentences every single time, which is fine for one go and
dull for the second. Two things changed:

  * Words are chosen from picture buttons, with "my own word" always there.
    A four-year-old can play the whole thing without touching a keyboard.
  * There are eight stories instead of one, each asking only the words it
    needs, and "same words, new story" re-runs what the child already picked
    through a different one — a new story for no extra typing.

The original story is still in here, as the first of the eight. The reference
implementation in terminal-games/ is untouched.

Everything below the data is a plain state machine: pick a story, fill its
slots, tell it, offer another.
"""

import random

from view import View, Prompt, Choice

ID = "silly-story"
TITLE = "Silly Story"
BLURB = "Pick some silly words and I'll make a story."
EMOJI = "📖"
MIN_AGE = 5

CHOOSING = "choosing"  # picking a word from buttons
TYPING = "typing"  # the child asked to write their own
ASK_AGAIN = "ask_again"
DONE = "done"

RULE = "-" * 30

# The value behind the "my own word" button. No real word can collide with it.
OWN_WORD = "__own__"

MAX_SUGGESTIONS = 5


# --- the words --------------------------------------------------------
#
# Each slot has a label for the buttons, a label for when the child would
# rather type, the prompt kind to use when they do, and a bank to sample
# suggestions from. Five are drawn fresh each time a slot is asked, so the
# same slot does not offer the same five twice in a row.

SLOTS = {
    "name": {
        "label": "Who is the story about?",
        "typed": "Type a name:",
        "kind": "text",
        "bank": [
            ("🙂", "Pip"),
            ("😀", "Bo"),
            ("😄", "Nell"),
            ("🤗", "Ziggy"),
            ("😎", "Juno"),
            ("🥳", "Wren"),
            ("🤠", "Otis"),
            ("🧐", "Mo"),
            ("😇", "Tilly"),
            ("🤓", "Fen"),
        ],
    },
    "animal": {
        "label": "Pick an animal!",
        "typed": "Type an animal:",
        "kind": "text",
        "bank": [
            ("🐧", "penguin"),
            ("🦕", "dinosaur"),
            ("🦥", "sloth"),
            ("🦙", "llama"),
            ("🐢", "turtle"),
            ("🐸", "frog"),
            ("🦩", "flamingo"),
            ("🐘", "elephant"),
            ("🐹", "hamster"),
            ("🐲", "dragon"),
        ],
    },
    "color": {
        "label": "Pick a colour!",
        "typed": "Type a colour:",
        "kind": "text",
        "bank": [
            ("🟣", "purple"),
            ("🟡", "gold"),
            ("🌈", "rainbow"),
            ("⚪", "silver"),
            ("🩷", "pink"),
            ("🟢", "green"),
            ("🟠", "orange"),
            ("🔵", "blue"),
            ("🐆", "spotty"),
            ("🦓", "stripy"),
        ],
    },
    "food": {
        "label": "Pick something yummy!",
        "typed": "Type a food:",
        "kind": "text",
        "bank": [
            ("🧇", "waffles"),
            ("🍝", "spaghetti"),
            ("🥦", "broccoli"),
            ("🧁", "cupcakes"),
            ("🍕", "pizza"),
            ("🥞", "pancakes"),
            ("🍦", "ice cream"),
            ("🍪", "cookies"),
            ("🥕", "carrots"),
            ("🍜", "noodles"),
        ],
    },
    "number": {
        "label": "How many?",
        "typed": "Type a number:",
        "kind": "number",
        "bank": [
            ("2️⃣", "2"),
            ("3️⃣", "3"),
            ("7️⃣", "7"),
            ("🔟", "10"),
            ("💯", "100"),
            ("🤯", "a MILLION"),
            ("0️⃣", "zero"),
            ("🎈", "55"),
        ],
    },
    "sound": {
        "label": "Make a silly sound!",
        "typed": "Type a silly sound:",
        "kind": "text",
        "bank": [
            ("💥", "splat"),
            ("📣", "honk"),
            ("🎺", "toot"),
            ("🤸", "boing"),
            ("🎢", "wheee"),
            ("🫧", "blorp"),
            ("🐭", "squeak"),
            ("💫", "ka-pow"),
            ("〰️", "wobble"),
            ("⚡", "zoink"),
        ],
    },
    "place": {
        "label": "Pick a place!",
        "typed": "Type a place:",
        "kind": "text",
        "bank": [
            ("🌙", "the moon"),
            ("🛁", "the bathtub"),
            ("🌳", "a treehouse"),
            ("🎩", "a big hat"),
            ("🛏️", "under the bed"),
            ("🏰", "a castle"),
            ("🌊", "the sea"),
            ("🍄", "a mushroom house"),
            ("🚀", "outer space"),
            ("❄️", "the North Pole"),
        ],
    },
    "thing": {
        "label": "Pick a thing!",
        "typed": "Type a thing:",
        "kind": "text",
        "bank": [
            ("🧦", "a sock"),
            ("🦆", "a rubber duck"),
            ("☂️", "an umbrella"),
            ("🫖", "a teapot"),
            ("🛹", "a skateboard"),
            ("🥄", "a spoon"),
            ("🎈", "a balloon"),
            ("📚", "a big book"),
            ("🪣", "a bucket"),
            ("🧸", "a teddy"),
        ],
    },
    "action": {
        "label": "Pick something to do!",
        "typed": "Type something to do:",
        "kind": "text",
        "bank": [
            ("💃", "dancing"),
            ("🤧", "sneezing"),
            ("😴", "snoring"),
            ("🌀", "spinning"),
            ("🤸", "hopping"),
            ("😂", "giggling"),
            ("🏊", "swimming"),
            ("🎤", "singing"),
            ("👏", "clapping"),
            ("🧗", "climbing"),
        ],
    },
    "feeling": {
        "label": "Pick a feeling!",
        "typed": "Type a feeling:",
        "kind": "text",
        "bank": [
            ("😴", "sleepy"),
            ("✨", "sparkly"),
            ("🫠", "squishy"),
            ("😠", "grumpy"),
            ("🎈", "bouncy"),
            ("🥶", "chilly"),
            ("🤪", "wobbly"),
            ("😊", "happy"),
            ("🦁", "brave"),
            ("🤫", "sneaky"),
        ],
    },
}


# --- the stories ------------------------------------------------------
#
# `slots` is both the list of words this story needs and the order they get
# asked in. Titles only ever use slots without an article in them, so they
# read properly. Add a story by adding a dict here — nothing else changes.

STORIES = [
    {
        # The original, word for word from terminal-games/mad_libs.py.
        "title": "The {color} {animal}",
        "art": "📖 ✨ 🎉 ✨ 📖",
        "slots": ["name", "animal", "color", "food", "number", "sound"],
        "lines": [
            "Once upon a time, {name} found a {color} {animal} in the backyard!",
            'The {animal} said, "{sound}!" and did a little dance.',
            "{name} was so surprised that they dropped their {food}.",
            "Then {number} more {animal}s showed up, all wearing tiny hats!",
            "Everyone laughed and had a {color} {food} party until bedtime.",
            "THE END!",
        ],
    },
    {
        "title": "{name} and the {animal}",
        "art": "🌙 ⭐ 😴 ⭐ 🌙",
        "slots": ["name", "animal", "place", "sound"],
        "lines": [
            "{name} could not sleep, so they tiptoed all the way to {place}.",
            "Guess who was already there? A very sleepy {animal}!",
            'It yawned a great big "{sound}!" and made room on the pillow.',
            "They both slept right through breakfast.",
            "THE END!",
        ],
    },
    {
        "title": "{name}'s Big Mix-Up",
        "art": "🙃 🔄 🙃 🔄 🙃",
        "slots": ["name", "thing", "food", "sound", "place"],
        "lines": [
            "One morning {name} got dressed in a terrible hurry.",
            "They put {thing} on their head instead of a hat!",
            "Then they packed {food} into their shoes instead of socks.",
            'Every single step went "{sound}!"',
            "Nobody said a word about it until they got to {place}.",
            "THE END!",
        ],
    },
    {
        "title": "The {feeling} {animal}",
        "art": "🏔️ 😾 🍽️ 😾 🏔️",
        "slots": ["animal", "feeling", "food", "sound"],
        "lines": [
            "There was once a very {feeling} {animal} who lived at the top of a hill.",
            "Nobody could cheer it up. Not with jokes. Not with tickles.",
            "So they left a plate of {food} by the door and hid behind a bush.",
            'The {animal} took one bite and shouted "{sound}!" so loudly '
            "that the birds fell out of the tree.",
            "It was never {feeling} again.",
            "THE END!",
        ],
    },
    {
        "title": "{name} Goes {action}",
        "art": "🗺️ 🧭 ⛰️ 🧭 🗺️",
        "slots": ["name", "action", "place", "animal"],
        "lines": [
            "{name} woke up and decided that today was a {action} sort of day.",
            "So off they went, all the way to {place}.",
            "A {animal} was already there, {action} in circles.",
            "They kept {action} together until the sun went down.",
            "THE END!",
        ],
    },
    {
        "title": "The Day the {animal} Came",
        "art": "🚪 👀 🎊 👀 🚪",
        "slots": ["animal", "number", "color", "sound", "place"],
        "lines": [
            "It started with one small knock at the door.",
            "Outside stood {number} {animal}s, every single one of them {color}.",
            'They all said "{sound}!" at exactly the same moment.',
            "They had walked the whole way from {place} just to say hello.",
            "Then they squeezed into the kitchen for a snack.",
            "THE END!",
        ],
    },
    {
        "title": "{name} and the {food}",
        "art": "🍽️ 😋 🥄 😋 🍽️",
        "slots": ["name", "food", "feeling", "sound"],
        "lines": [
            "{name} was feeling extremely {feeling}, so they made {food} for dinner.",
            "They made SO MUCH {food} that it filled the entire bathtub.",
            'The very first bite went "{sound}!"',
            "All the neighbours came round with spoons and helped finish it.",
            "THE END!",
        ],
    },
    {
        "title": "The {sound} Mystery",
        "art": "🔍 ❓ 🌑 ❓ 🔍",
        "slots": ["sound", "name", "thing", "animal"],
        "lines": [
            'All night long the house went "{sound}... {sound}..."',
            "{name} crept downstairs with a torch to find out why.",
            "Under the stairs they found {thing}, wobbling all by itself.",
            "And behind it, trying very hard to look innocent, was a {animal}.",
            "THE END!",
        ],
    },
]


class _Words(dict):
    """A slot with no word in it yields a silly one rather than a KeyError.
    send() is not allowed to raise, not even over a typo in a story."""

    def __missing__(self, key: str) -> str:
        return "something"


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
        """A brand new game: fresh story, no words. Re-seeding here is what
        makes start() repeatable — call it twice and you get the same story,
        which is what the contract asks for. With no seed, Random() draws
        fresh entropy each time, so a real child gets a new story."""
        self.rng = random.Random(self._seed)
        self._lines: list[str] = []
        self.state = CHOOSING
        self.story = self.rng.randrange(len(STORIES))
        self.words: dict[str, str] = {}
        self.slot = ""

    def _fill(self, text: str) -> str:
        # Only the template is parsed for placeholders, so a child who types
        # "{name}" or "%s" just gets those characters back in their story.
        return text.format_map(_Words(self.words))

    # --- the game -------------------------------------------------------

    def start(self) -> View:
        self._reset()
        self.say("Let's make a SILLY story together!")
        self.say("Pick some words, then watch the magic happen...")
        return self._next_slot()

    def _new_story(self) -> View:
        """Another story in the same sitting. Deliberately not start(): the
        child has already read the how-to-play lines and the transcript keeps
        the last story right above, so repeating the intro is just noise.

        start() stays untouched so it remains idempotent — which is also why
        the never-twice-in-a-row rule lives here and not in _reset()."""
        previous = self.story
        self._reset()
        if len(STORIES) > 1 and self.story == previous:
            self.story = self.rng.choice(
                [i for i in range(len(STORIES)) if i != previous]
            )
        self.say("Yay! Let's make another one!")
        return self._next_slot()

    def _next_slot(self) -> View:
        """Ask for the first word this story still needs, or tell the story.
        Scanning rather than counting is what lets a remix skip everything
        the child has already picked."""
        for slot in STORIES[self.story]["slots"]:
            if slot not in self.words:
                self.slot = slot
                self.state = CHOOSING
                return self._ask_choices()
        return self._tell_story()

    def _ask_choices(self) -> View:
        slot = SLOTS[self.slot]
        bank = slot["bank"]
        picks = self.rng.sample(bank, min(MAX_SUGGESTIONS, len(bank)))
        choices = [Choice(f"{emoji} {word}", word) for emoji, word in picks]
        choices.append(Choice("✏️ My own word", OWN_WORD))
        return self._flush(
            Prompt(kind="choice", label=slot["label"], choices=choices)
        )

    def _ask_typed(self) -> View:
        slot = SLOTS[self.slot]
        return self._flush(Prompt(kind=slot["kind"], label=slot["typed"]))

    def send(self, value: str) -> View:
        if self.state == DONE:
            return self.start()
        handler = getattr(self, f"_on_{self.state}", None)
        if handler is None:  # pragma: no cover - unreachable while states match
            return self.start()
        return handler(value.strip())

    def _on_choosing(self, value: str) -> View:
        if value == OWN_WORD:
            self.state = TYPING
            return self._ask_typed()
        if not value:
            self.say("Pick one, or tap “My own word”!")
            return self._ask_choices()
        # The buttons are shortcuts, not a list of the only allowed answers —
        # which is what keeps this typeable in a terminal.
        self.words[self.slot] = value
        return self._next_slot()

    def _on_typing(self, value: str) -> View:
        if not value:
            self.say("I didn't catch that one — give me a word!")
            return self._ask_typed()
        self.words[self.slot] = value
        return self._next_slot()

    # --- the payoff -----------------------------------------------------

    def _tell_story(self) -> View:
        story = STORIES[self.story]
        title = self._fill(story["title"])

        self.say("")
        self.say("Here is your story...")
        self.say(RULE)
        self.say(f"🌟 {title[:1].upper()}{title[1:]} 🌟")
        self.say("")
        for line in story["lines"]:
            self.say(self._fill(line))
        self.say(RULE)

        self.state = ASK_AGAIN
        return self._flush(self._what_next(), art=story["art"], sound="win")

    @staticmethod
    def _what_next() -> Prompt:
        return Prompt(
            kind="choice",
            label="What next?",
            choices=[
                Choice("📖 A new story", "new"),
                Choice("🎲 Same words, new story", "remix"),
                Choice("✅ I'm done", "done"),
            ],
        )

    def _on_ask_again(self, value: str) -> View:
        answer = value.lower()

        if answer in ("remix", "same", "r"):
            return self._remix()

        if answer in ("done", "no", "n", "stop", "q", "quit"):
            self.say("Thanks for playing! Bye bye!")
            self.state = DONE
            return self._flush(Prompt(kind="end", label="Another story?"))

        if answer in ("new", "yes", "y"):
            return self._new_story()

        # Anything else: ask again rather than silently throwing the story away.
        self.say("Pick one of these!")
        return self._flush(self._what_next())

    def _remix(self) -> View:
        """Keep every word the child has picked and run them through a
        different story. Words pile up as they go, so the second remix
        usually asks for nothing at all."""
        others = [i for i in range(len(STORIES)) if i != self.story]
        self.story = self.rng.choice(others)
        self.say("Same words, brand new story!")
        return self._next_slot()
