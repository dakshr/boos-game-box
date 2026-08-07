import random

print("Welcome to the Secret Number Game!")
print("I'm thinking of a number between 1 and 20...")

secret_number = random.randint(1, 20)
guess = 0
tries = 0

while guess != secret_number:
    guess = int(input("What's your guess? "))
    tries += 1

    if guess < secret_number:
        print("Too low! Try a bigger number.")
    elif guess > secret_number:
        print("Too high! Try a smaller number.")
    else:
        print(f"YOU GOT IT! The number was {secret_number}!")
        print(f"You found it in {tries} tries!")

        if tries <= 3:
            print("WOW! You're a guessing SUPERSTAR!")
        elif tries <= 6:
            print("Great job, you smart cookie!")
        else:
            print("You did it! Practice makes perfect!")
