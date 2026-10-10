import random


def create_game(digits=4, attempts=15):
    """Create a secret combination with unique digits and an attempt limit."""
    if not isinstance(digits, int) or not 1 <= digits <= 10:
        raise ValueError("digits must be an integer from 1 to 10")
    if not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be a positive integer")

    secret = "".join(random.sample("0123456789", digits))
    return {
        "secret": secret,
        "attempts": attempts,
        "attempts_left": attempts,
        "finished": False,
        "digits": digits,
        "max_attempts": attempts,
    }


def check_guess(game, guess):
    """Validate and score a guess for a secret with unique digits."""
    if game.get("finished", False):
        return {
            "valid": False,
            "correct": False,
            "message": "This game has already finished.",
        }

    guess = str(guess).strip()
    secret = str(game["secret"])

    if (
        not guess.isdigit()
        or len(guess) != len(secret)
        or len(set(guess)) != len(guess)
    ):
        return {
            "valid": False,
            "correct": False,
            "message": (
                f"Please enter exactly {len(secret)} digits, "
                "with no repeated digits."
            ),
        }

    if guess == secret:
        game["finished"] = True
        return {
            "valid": True,
            "correct": True,
            "message": "Correct! You guessed the combination!",
        }

    correct_position = sum(a == b for a, b in zip(secret, guess))
    correct_digit = sum(digit in secret for digit in guess)
    game["attempts_left"] = game.get(
        "attempts_left", game.get("attempts", 15)
    ) - 1
    game["attempts"] = game["attempts_left"]

    if game["attempts_left"] <= 0:
        game["finished"] = True
        message = f"Game over! The combination was {secret}."
    else:
        message = (
            f"Correct digits: {correct_digit}\n"
            f"Correct positions: {correct_position}\n"
            f"Attempts remaining: {game['attempts_left']}"
        )

    return {
        "valid": True,
        "correct": False,
        "message": message,
    }
