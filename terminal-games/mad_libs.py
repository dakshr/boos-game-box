print("Let's make a SILLY story together!")
print("I'll ask you for some words, then watch the magic happen...")
print()

name = input("Give me a kid's name: ")
animal = input("Name an animal: ")
color = input("Name a color: ")
food = input("Name a yummy food: ")
number = input("Give me a number: ")
silly_sound = input("Make a silly sound (like 'boing' or 'wheee'): ")

print()
print("Here is your story...")
print("-" * 30)
print(f"Once upon a time, {name} found a {color} {animal} in the backyard!")
print(f'The {animal} said, "{silly_sound}!" and did a little dance.')
print(f"{name} was so surprised that they dropped their {food}.")
print(f"Then {number} more {animal}s showed up, all wearing tiny hats!")
print(f"Everyone laughed and had a {color} {food} party until bedtime.")
print("THE END!")
print("-" * 30)

again = input("Want to make another story? (yes/no): ")
if again.lower().startswith("y"):
    print("Yay! Run me again for a brand new silly story!")
else:
    print("Thanks for playing! Bye bye!")
