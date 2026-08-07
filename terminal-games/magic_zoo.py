#!/usr/bin/env python3
"""
Magic Zoo - A tiny game for 5-6 year olds!
Just run it and press numbers to play.

Run: python3 magic_zoo.py
"""

import random
import time

# Our animal friends
ANIMALS = {
    "1": {"emoji": "🐶", "name": "Puppy", "sound": "WOOF WOOF!", "color": "\033[93m"},
    "2": {"emoji": "🐱", "name": "Kitty", "sound": "MEOW~!", "color": "\033[95m"},
    "3": {"emoji": "🦁", "name": "Lion", "sound": "ROARRR!", "color": "\033[91m"},
    "4": {"emoji": "🐵", "name": "Monkey", "sound": "OOO AAA AAA!", "color": "\033[92m"},
    "5": {"emoji": "🐘", "name": "Elephant", "sound": "PAAAAA!", "color": "\033[94m"},
    "6": {"emoji": "🐧", "name": "Penguin", "sound": "WADDLE WADDLE!", "color": "\033[96m"},
}

RESET = "\033[0m"
BOLD = "\033[1m"
RAINBOW = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]

CELEBRATIONS = [
    "✨ ⭐ ✨ ⭐ ✨",
    "🌈 🌟 🌈 🌟 🌈",
    "🎉 🎊 🎉 🎊 🎉",
    "💫 ⭐ 💫 ⭐ 💫",
    "🌸 🌼 🌸 🌼 🌸",
]

FOODS = ["🍎", "🍌", "🍓", "🥕", "🍪", "🧁", "🍭"]

def clear():
    print("\n" * 2)

def rainbow_text(text):
    out = ""
    for i, ch in enumerate(text):
        out += RAINBOW[i % len(RAINBOW)] + ch
    return out + RESET

def big_banner():
    print(rainbow_text("  ╔════════════════════════════╗"))
    print(rainbow_text("  ║   🌈  MAGIC ZOO  🌈       ║"))
    print(rainbow_text("  ╚════════════════════════════╝"))
    print()

def show_menu():
    print(BOLD + "  Pick a friend! Type the NUMBER and press ENTER:\n" + RESET)
    for key, a in ANIMALS.items():
        print(f"    {a['color']}{key}  {a['emoji']}  {a['name']}{RESET}   ", end="")
        if key in ("3", "6"):
            print()
    print("\n")
    print("    0  🎨  RAINBOW SURPRISE!")
    print("    q  👋  Bye bye")
    print()

def celebrate(animal):
    c = random.choice(CELEBRATIONS)
    food = random.choice(FOODS)
    print()
    print(f"  {animal['color']}{c}{RESET}")
    print(f"  {animal['color']}  {animal['emoji']} {animal['name']} says: {animal['sound']}  {animal['emoji']}{RESET}")
    print(f"  {animal['color']}  You gave {animal['name']} a {food}  Yummy!{RESET}")
    # funny little bounce
    for _ in range(2):
        print(f"    {animal['emoji']}  " + " ".join([animal['emoji']] * 3))
        time.sleep(0.15)
    print(f"  {animal['color']}{c}{RESET}")
    print()

def rainbow_surprise():
    print()
    print(rainbow_text("  ✨ WOW! RAINBOW TIME! ✨"))
    for _ in range(3):
        line = "".join(random.choice(["🌈","⭐","✨","🌟","💫"]) for _ in range(12))
        print("   " + rainbow_text(line))
        time.sleep(0.2)
    print(rainbow_text("  You found the magic rainbow! 🌈"))
    print()

def main():
    clear()
    big_banner()
    print("  Hi there, super star! ⭐")
    print("  Let's play with cute animals!\n")
    time.sleep(0.5)

    stars = 0
    while True:
        show_menu()
        choice = input("  👉 Your pick: ").strip().lower()

        if choice in ("q", "quit", "bye", "exit"):
            print()
            print(rainbow_text(f"  Bye bye! You collected {stars} ⭐  Come back soon! 👋"))
            print(rainbow_text("  🌈 ✨ 🐶 🐱 🦁 🐵 🐘 🐧 ✨ 🌈"))
            break
        elif choice == "0":
            rainbow_surprise()
            stars += 3
            print(f"  You have {stars} ⭐\n")
        elif choice in ANIMALS:
            celebrate(ANIMALS[choice])
            stars += 1
            print(f"  You have {stars} ⭐  Keep going!\n")
            # every 5 stars, extra party
            if stars % 5 == 0:
                print(BOLD + f"  🎉 WOW! {stars} stars! PARTY TIME! 🎉" + RESET)
                rainbow_surprise()
        else:
            # be very forgiving - try to find animal by name or emoji
            found = None
            for k, a in ANIMALS.items():
                if choice in a["name"].lower() or choice == a["emoji"]:
                    found = a
                    break
            if found:
                celebrate(found)
                stars += 1
                print(f"  You have {stars} ⭐\n")
            else:
                print("\n  Oops! Try a number 1-6, or 0 for a surprise! 🌟\n")
                time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Bye bye! 🌈 👋\n")
