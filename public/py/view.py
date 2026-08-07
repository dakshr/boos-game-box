"""The View / Prompt contract.

Every game returns a `View`. A View says two things and nothing else:
what to display, and what to ask next. It never says how anything looks —
that is the shell's job, and the shell might be a browser, a terminal,
or a test.

Standard library only. This module is imported by every game.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional

PromptKind = Literal["choice", "number", "text", "continue", "end"]


@dataclass
class Choice:
    """One button."""

    label: str  # what the child sees on the button
    value: str  # what gets sent back to the game


@dataclass
class Prompt:
    """What the game is waiting for.

    kind == "choice"   -> render `choices` as buttons
    kind == "number"   -> numeric entry, honouring `min`/`max` as hints
    kind == "text"     -> free text entry
    kind == "continue" -> a single "Next" button (pacing; replaces
                          `input("Press enter...")` and `time.sleep()`)
    kind == "end"      -> "Play again" / "Back to the box"; game is over
    """

    kind: PromptKind
    label: str = ""  # e.g. "Pick a color"
    choices: list[Choice] = field(default_factory=list)  # kind == "choice"
    min: Optional[int] = None  # kind == "number"
    max: Optional[int] = None


@dataclass
class View:
    """One turn of output."""

    lines: list[str]  # what to display, newest last
    prompt: Prompt
    art: Optional[str] = None  # optional emoji/ASCII banner, monospaced
    sound: Optional[str] = None  # "correct" | "wrong" | "win" — shell may ignore
    score: Optional[int] = None
