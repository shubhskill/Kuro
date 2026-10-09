import random

def create_game():
"""Create a new Number Combination game session."""
return {
"secret": "".join(str(random.randint(0, 9)) for _ in range(4)),
"attempts_left": 8,
"max_attempts": 8,
"finished": False,
}

def check_guess(game, guess):
"""Check a four-digit guess and return feedback."""
if game["finished"]:
return {"status": "finished", "message": "This game has ended."}

```
if not guess.isdigit() or len(guess) != 4:
    return {
        "status": "invalid",
        "message": "Enter exactly 4 digits, for example: 1234.",
    }

secret = game["secret"]
correct_position = sum(
    secret[i] == guess[i] for i in range(4)
)
correct_digit = sum(
    min(secret.count(digit), guess.count(digit))
    for digit in set(guess)
)

game["attempts_left"] -= 1

if guess == secret:
    game["finished"] = True
    return {
        "status": "won",
        "message": (
            "🎉 Correct! You cracked the combination!\n"
            f"Attempts used: "
            f"{game['max_attempts'] - game['attempts_left']}"
        ),
    }

if game["attempts_left"] <= 0:
    game["finished"] = True
    return {
        "status": "lost",
        "message": (
            f"❌ No attempts left!\n"
            f"The secret combination was {secret}."
        ),
    }

return {
    "status": "playing",
    "message": (
        f"🎯 Correct digits in the correct position: "
        f"{correct_position}\n"
        f"🔎 Correct digits in any position: {correct_digit}\n"
        f"❤️ Attempts remaining: {game['attempts_left']}"
    ),
}
```
