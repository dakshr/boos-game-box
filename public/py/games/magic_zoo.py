"""Magic Zoo — refactor of terminal-games/magic_zoo.py.

Same animals, same sounds, same star counting, same party at every fifth
star, same forgiving matching on names and emoji.

Two things the terminal version had that a browser doesn't need:
  * ANSI colour codes — dropped, the shell paints the screen now.
  * `time.sleep()` bounces — dropped; the lines still print, just at once.

The typed menu becomes buttons, but the values behind them ("1".."6",
"0", "q") are exactly the strings the original accepted.
"""

import random

from view import View, Prompt, Choice

ID = "magic-zoo"
TITLE = "Magic Zoo"
BLURB = "Pick an animal friend and hear what it says."
EMOJI = "🦁"
MIN_AGE = 4

PLAYING = "playing"
DONE = "done"

# Our animal friends
ANIMALS = {
    "1": {"emoji": "🐶", "name": "Puppy", "sound": "WOOF WOOF!"},
    "2": {"emoji": "🐱", "name": "Kitty", "sound": "MEOW~!"},
    "3": {"emoji": "🦁", "name": "Lion", "sound": "ROARRR!"},
    "4": {"emoji": "🐵", "name": "Monkey", "sound": "OOO AAA AAA!"},
    "5": {"emoji": "🐘", "name": "Elephant", "sound": "PAAAAA!"},
    "6": {"emoji": "🐧", "name": "Penguin", "sound": "WADDLE WADDLE!"},
}

CELEBRATIONS = [
    "✨ ⭐ ✨ ⭐ ✨",
    "🌈 🌟 🌈 🌟 🌈",
    "🎉 🎊 🎉 🎊 🎉",
    "💫 ⭐ 💫 ⭐ 💫",
    "🌸 🌼 🌸 🌼 🌸",
]

FOODS = ["🍎", "🍌", "🍓", "🥕", "🍪", "🧁", "🍭"]

SPARKLES = ["🌈", "⭐", "✨", "🌟", "💫"]

QUIT_WORDS = ("q", "quit", "bye", "exit")

# The original's middle line was one column short of its own borders (the
# ANSI colouring hid it). Counting an emoji as two columns, as a terminal
# does, it needs one more space before the closing bar.
BANNER = "\n".join(
    [
        "╔════════════════════════════╗",
        "║   🌈  MAGIC ZOO  🌈        ║",
        "╚════════════════════════════╝",
    ]
)


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
        self.state = PLAYING
        self.stars = 0

    # --- the game -------------------------------------------------------

    def start(self) -> View:
        self._reset()
        self.say("Hi there, super star! ⭐")
        self.say("Let's play with cute animals!")
        return self._menu(art=BANNER)

    def _menu(self, **kw) -> View:
        choices = [
            Choice(f"{a['emoji']}  {a['name']}", key) for key, a in ANIMALS.items()
        ]
        choices.append(Choice("🎨  RAINBOW SURPRISE!", "0"))
        choices.append(Choice("👋  Bye bye", "q"))
        return self._flush(
            Prompt(kind="choice", label="Pick a friend!", choices=choices),
            score=self.stars,
            **kw,
        )

    def send(self, value: str) -> View:
        if self.state == DONE:
            return self.start()

        choice = value.strip().lower()

        if choice in QUIT_WORDS:
            return self._goodbye()

        if choice == "0":
            self._rainbow_surprise()
            self.stars += 3
            self.say(f"You have {self.stars} ⭐")
            return self._menu(sound="win")

        if choice in ANIMALS:
            self._celebrate(ANIMALS[choice])
            self.stars += 1
            self.say(f"You have {self.stars} ⭐  Keep going!")
            # every 5 stars, extra party
            if self.stars % 5 == 0:
                self.say(f"🎉 WOW! {self.stars} stars! PARTY TIME! 🎉")
                self._rainbow_surprise()
                return self._menu(sound="win")
            return self._menu(sound="correct")

        # be very forgiving - try to find animal by name or emoji
        found = None
        for _key, animal in ANIMALS.items():
            if choice in animal["name"].lower() or choice == animal["emoji"]:
                found = animal
                break
        if found:
            self._celebrate(found)
            self.stars += 1
            self.say(f"You have {self.stars} ⭐")
            return self._menu(sound="correct")

        self.say("Oops! Try a number 1-6, or 0 for a surprise! 🌟")
        return self._menu()

    # --- the fun bits ---------------------------------------------------

    def _celebrate(self, animal: dict) -> None:
        c = self.rng.choice(CELEBRATIONS)
        food = self.rng.choice(FOODS)
        self.say("")
        self.say(c)
        self.say(f"  {animal['emoji']} {animal['name']} says: {animal['sound']}  {animal['emoji']}")
        self.say(f"  You gave {animal['name']} a {food}  Yummy!")
        # funny little bounce
        for _ in range(2):
            self.say(f"  {animal['emoji']}  " + " ".join([animal["emoji"]] * 3))
        self.say(c)
        self.say("")

    def _rainbow_surprise(self) -> None:
        self.say("")
        self.say("✨ WOW! RAINBOW TIME! ✨")
        for _ in range(3):
            self.say(" " + "".join(self.rng.choice(SPARKLES) for _ in range(12)))
        self.say("You found the magic rainbow! 🌈")
        self.say("")

    def _goodbye(self) -> View:
        self.say("")
        self.say(f"Bye bye! You collected {self.stars} ⭐  Come back soon! 👋")
        self.say("🌈 ✨ 🐶 🐱 🦁 🐵 🐘 🐧 ✨ 🌈")
        self.state = DONE
        return self._flush(
            Prompt(kind="end", label="Play again?"),
            score=self.stars,
        )
