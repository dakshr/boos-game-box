#!/usr/bin/env python3
"""
Calm Math Garden - for 5-6 year olds

Solve a little math, plant your garden.
No flashing, no rush. Just counting and choosing.

Run: python3 garden.py
"""

import random

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

def make_problem():
    """Return (question_text, hint_text, answer) for a 5-6 year old."""
    kind = random.choice(["add", "add", "sub", "sub", "count"])

    if kind == "add":
        a = random.randint(1, 5)
        b = random.randint(1, 5)
        # keep sum <= 10 for this age
        while a + b > 10:
            a = random.randint(1, 5)
            b = random.randint(1, 5)
        q = f"{a} + {b} = ?"
        hint = f"  hint: {'●' * a}  +  {'●' * b}  -> count all the dots"
        ans = a + b

    elif kind == "sub":
        a = random.randint(3, 10)
        b = random.randint(1, a - 1)
        # avoid 0 answer too often, keep it 1+
        if a - b == 0:
            b -= 1
        q = f"{a} - {b} = ?"
        hint = f"  hint: start at {a}, count back {b} -> {'●' * a} take away {'●' * b}"
        ans = a - b

    else:  # count - visual apples
        a = random.randint(1, 4)
        b = random.randint(1, 4)
        while a + b > 9:
            a = random.randint(1, 4)
            b = random.randint(1, 4)
        q = f"{'🍎' * a} + {'🍎' * b} = ?  (how many apples?)"
        hint = f"  hint: {a} apples and {b} more"
        ans = a + b

    return q, hint, ans


def show_garden(garden):
    print("\n  Your garden (1-9):")
    print("  +----+----+----+")
    for r in range(3):
        row = garden[r*3:(r+1)*3]
        # show numbers for empty, emoji for planted — both 4 visual cols so pipes line up
        # number: " 1  " is 1+1+2 spaces = 4 cols; emoji: " 🌼 " is 1+2+1 = 4 cols (emoji is double-width)
        cells = []
        for i, cell in enumerate(row):
            idx = r*3 + i + 1
            if cell == ".":
                cells.append(f" {idx}  ")
            else:
                cells.append(f" {cell} ")
        print("  |" + "|".join(cells) + "|")
        print("  +----+----+----+")
    print()


def main():
    print("\n  Welcome to the Calm Math Garden")
    print("  -------------------------------")
    print("  Solve a little math, then choose what to plant.")
    print("  No hurry. Take your time.\n")

    garden = ["."] * SIZE
    solved = 0

    # ask name just for friendliness - optional
    try:
        name = input("  What is your name? (press Enter to skip): ").strip()
    except EOFError:
        name = ""
    if name:
        print(f"\n  Hello, {name}! Let's grow a garden together.\n")
    else:
        print(f"\n  Let's grow a garden together.\n")

    planted = 0

    while planted < SIZE:
        q, hint, ans = make_problem()
        print(f"  --- Garden plot {planted+1} of {SIZE} ---")
        print(f"  Question: {q}")

        # first try
        try:
            raw = input("  Your answer: ").strip().lower()
        except EOFError:
            raw = "q"
        if raw in ("q", "quit", "exit", "bye"):
            print("\n  You can come back anytime. Your garden will wait.\n")
            break

        # allow empty
        if raw == "":
            print("  Try typing a number. You can do it.")
            continue

        # check numeric
        try:
            given = int(raw)
        except ValueError:
            print("  Please type a number, like 5 or 7.")
            continue

        if given == ans:
            print("  Correct! Nice counting.\n")
            solved += 1
        else:
            # gentle second chance with hint
            print(f"  Not quite. {hint}")
            print(f"  Try once more. What is {q}")
            try:
                raw2 = input("  Your answer: ").strip()
            except EOFError:
                raw2 = ""
            if raw2 in ("q", "quit", "exit"):
                print("\n  Pausing here. Bye for now.\n")
                break
            try:
                given2 = int(raw2)
            except ValueError:
                given2 = None

            if given2 == ans:
                print("  You got it on the second try. Good persistence.\n")
                solved += 1
            else:
                print(f"  The answer was {ans}. Good try — counting is hard and you kept going.\n")
                # still let them plant to keep it encouraging
                solved += 0  # not counted as solved, but still creative turn

        # creative choice: what to plant
        show_garden(garden)
        print("  You earned a seed! What would you like to plant?")
        for k in sorted(PLANTS):
            print(f"    {k} - {PLANTS[k]} {PLANT_NAMES[k]}")
        choice = ""
        while choice not in PLANTS:
            try:
                choice = input("  Pick 1-4: ").strip()
            except EOFError:
                choice = "1"
            if choice not in PLANTS:
                print("  Pick 1, 2, 3, or 4.")

        # where to plant
        empty = [str(i+1) for i, v in enumerate(garden) if v == "."]
        print(f"  Where should it grow? Empty plots: {', '.join(empty)}")
        where = ""
        while where not in empty:
            try:
                where = input("  Pick plot number: ").strip()
            except EOFError:
                where = empty[0]
            if where not in empty:
                print(f"  Choose an empty plot from: {', '.join(empty)}")

        garden[int(where)-1] = PLANTS[choice]
        planted += 1
        print(f"  Planted a {PLANT_NAMES[choice]} {PLANTS[choice]} in plot {where}.")
        show_garden(garden)

        if planted < SIZE:
            try:
                nxt = input("  Press Enter to keep planting, or type q to stop: ").strip().lower()
            except EOFError:
                nxt = "q"
            if nxt == "q":
                break
            print()

    # closing
    print("\n  -------------------------------")
    print(f"  Finished! You solved {solved} problem(s) and planted {planted} seed(s).")
    show_garden(garden)
    if planted == SIZE:
        print("  Your garden is full. You built it with math and choices.")
    else:
        print("  Come back to finish your garden whenever you like.")
    print("  Bye, gardener!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Garden paused. Bye!\n")
