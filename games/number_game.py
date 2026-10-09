
import random



def create_game():
    """Create a new game with unique digits."""
    secret = "".join(
        random.sample("0123456789", 4)
    )

    return {
        "secret": secret,
        "attempts": 8,
        "finished": False,
        "digits": 4,
        "max_attempts": 8,
    }

def check_guess(game, guess):
    """Check a player's guess against the secret number."""
    if game.get("finished", False):
        return {
            "valid": False,
            "message": "This game has already finished.",
        }

    guess = str(guess).strip()
    secret = str(game["secret"])

    if not guess.isdigit() or len(guess) != len(secret):
        return {
            "valid": False,
            "message": f"Please enter exactly {len(secret)} digits.",
        }

    if guess == secret:
        game["finished"] = True
        return {
            "valid": True,
            "correct": True,
            "message": "Correct! You guessed the combination!",
        }

    correct_position = sum(
        1 for i in range(len(secret)) if guess[i] == secret[i]
    )

    correct_digit = sum(
        min(guess.count(digit), secret.count(digit))
        for digit in set(guess)
    )

    game["attempts"] -= 1

    if game["attempts"] <= 0:
        game["finished"] = True
        message = f"Game over! The combination was {secret}."
    else:
        message = (
            f"Correct digits: {correct_digit}\n"
            f"Correct positions: {correct_position}\n"
            f"Attempts remaining: {game['attempts']}"
        )

    return {
        "valid": True,
        "correct": False,
        "message": message,
    }
