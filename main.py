import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Update
from telegram.ext import (
Application,
CallbackQueryHandler,
CommandHandler,
ContextTypes,
MessageHandler,
filters,
)

from games.number_game import create_game, check_guess

logging.basicConfig(
format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
level=logging.INFO,
)
logger = logging.getLogger("kuro")

GAMES = {
"number": ("🔢 Number Combination", "Crack a secret number combination."),
"riddles": ("🧩 Riddles", "Solve riddles and test your brain."),
"battle": ("⚔️ 1v1 Battle", "Challenge another player to a battle."),
"racing": ("🏎️ Racing", "Compete against other players in a race."),
"imposter": ("🕵️ Imposter", "Find the hidden imposter in your group."),
}

def main_menu_keyboard():
return InlineKeyboardMarkup([
[
InlineKeyboardButton("🔢 Number Combination", callback_data="game:number"),
InlineKeyboardButton("🧩 Riddles", callback_data="game:riddles"),
],
[
InlineKeyboardButton("⚔️ 1v1 Battle", callback_data="game:battle"),
InlineKeyboardButton("🏎️ Racing", callback_data="game:racing"),
],
[InlineKeyboardButton("🕵️ Imposter", callback_data="game:imposter")],
[
InlineKeyboardButton("👤 My Profile", callback_data="profile"),
InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
],
[InlineKeyboardButton("🚪 Logout", callback_data="logout")],
])

def back_keyboard():
return InlineKeyboardMarkup([
[InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
[InlineKeyboardButton("🚪 Logout", callback_data="logout")],
])

def difficulty_keyboard():
return InlineKeyboardMarkup([
[
InlineKeyboardButton("🟢 Easy (4 digits)", callback_data="number:start:4:10"),
],
[
InlineKeyboardButton("🟡 Medium (5 digits)", callback_data="number:start:5:10"),
],
[
InlineKeyboardButton("🔴 Hard (6 digits)", callback_data="number:start:6:12"),
],
[InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
[InlineKeyboardButton("🚪 Logout", callback_data="logout")],
])

def game_keyboard():
return InlineKeyboardMarkup([
[InlineKeyboardButton("🔄 New Game", callback_data="game:number")],
[InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
[InlineKeyboardButton("🚪 Logout", callback_data="logout")],
])

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = (
"🖤 WELCOME TO KURO\n\n"
"Your games. Your arena. Your leaderboard.\n\n"
"🎮 Choose a game from the menu below!"
)

```
if update.callback_query:
    await update.callback_query.edit_message_text(
        text=text, reply_markup=main_menu_keyboard()
    )
else:
    await update.effective_message.reply_text(
        text=text, reply_markup=main_menu_keyboard()
    )
```

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data.clear()
await show_menu(update, context)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
await show_menu(update, context)

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data.clear()
text = (
"🚪 KURO session reset.\n\n"
"Your temporary game session has been cleared.\n"
"Account login is not enabled in this version."
)
if update.callback_query:
await update.callback_query.edit_message_text(
text=text, reply_markup=back_keyboard()
)
else:
await update.effective_message.reply_text(
text=text, reply_markup=back_keyboard()
)

async def begin_number_game(
update: Update, context: ContextTypes.DEFAULT_TYPE, digits: int, attempts: int
):
game = create_game()
game["secret"] = "".join(
**import**("random").choice("0123456789") for _ in range(digits)
)
game["attempts_left"] = attempts
game["max_attempts"] = attempts
game["digits"] = digits
game["finished"] = False

```
context.user_data["number_game"] = game

await update.callback_query.edit_message_text(
    f"🔢 NUMBER COMBINATION — {'EASY' if digits == 4 else 'MEDIUM' if digits == 5 else 'HARD'}\n\n"
    f"I've picked a secret {digits}-digit combination.\n"
    f"You have {attempts} attempts to crack it.\n\n"
    "Send your guess as a message containing exactly "
    f"{digits} digits.\n\n"
    "💡 After each guess, you'll get hints.",
    reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
        [InlineKeyboardButton("🚪 Logout", callback_data="logout")],
    ]),
)
```

async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
game = context.user_data.get("number_game")
if not game or game.get("finished"):
return

```
guess = (update.effective_message.text or "").strip()
digits = game["digits"]

if not guess.isdigit() or len(guess) != digits:
    await update.effective_message.reply_text(
        f"Please enter exactly {digits} digits, for example: "
        + ("1234" if digits == 4 else "12345" if digits == 5 else "123456")
    )
    return

result = check_guess(game, guess)

# The game module validates four digits, so handle other difficulty lengths here.
if result["status"] == "invalid":
    secret = game["secret"]
    correct_position = sum(a == b for a, b in zip(secret, guess))
    correct_digit = sum(
        min(secret.count(d), guess.count(d)) for d in set(guess)
    )
    game["attempts_left"] -= 1

    if guess == secret:
        game["finished"] = True
        result = {
            "status": "won",
            "message": "🎉 Correct! You cracked the combination!",
        }
    elif game["attempts_left"] <= 0:
        game["finished"] = True
        result = {
            "status": "lost",
            "message": f"❌ No attempts left! The secret was {secret}.",
        }
    else:
        result = {
            "status": "playing",
            "message": (
                f"🎯 Correct digits in correct positions: {correct_position}\n"
                f"🔎 Correct digits in any position: {correct_digit}\n"
                f"❤️ Attempts remaining: {game['attempts_left']}"
            ),
        }

if result["status"] in ("won", "lost"):
    await update.effective_message.reply_text(
        result["message"], reply_markup=game_keyboard()
    )
else:
    await update.effective_message.reply_text(result["message"])
```

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
data = query.data

```
if data == "menu":
    await show_menu(update, context)
    return

if data == "logout":
    await logout(update, context)
    return

if data == "game:number":
    context.user_data.pop("number_game", None)
    await query.edit_message_text(
        "🔢 NUMBER COMBINATION\n\nChoose your difficulty:",
        reply_markup=difficulty_keyboard(),
    )
    return

if data.startswith("number:start:"):
    try:
        _, _, digits, attempts = data.split(":")
        await begin_number_game(update, context, int(digits), int(attempts))
    except (ValueError, IndexError):
        await query.edit_message_text(
            "Could not start that game.", reply_markup=back_keyboard()
        )
    return

if data.startswith("game:"):
    game_id = data.split(":", 1)[1]
    game = GAMES.get(game_id)
    if game:
        await query.edit_message_text(
            f"{game[0]}\n\n{game[1]}\n\n"
            "🚧 This game will be implemented in a future step.",
            reply_markup=back_keyboard(),
        )
    else:
        await query.edit_message_text(
            "Game not found.", reply_markup=back_keyboard()
        )
    return

if data == "profile":
    await query.edit_message_text(
        "👤 MY PROFILE\n\nProfiles will be connected when the database is configured.",
        reply_markup=back_keyboard(),
    )
    return

if data == "leaderboard":
    await query.edit_message_text(
        "🏆 LEADERBOARD\n\nRankings will appear after scoring and database setup.",
        reply_markup=back_keyboard(),
    )
    return

await query.edit_message_text(
    "Unknown option. Please return to the main menu.",
    reply_markup=back_keyboard(),
)
```

async def post_init(application: Application):
await application.bot.set_my_commands([
BotCommand("start", "Open KURO"),
BotCommand("menu", "Show the main menu"),
BotCommand("logout", "Reset your temporary session"),
])
logger.info("KURO bot commands registered.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
logger.error("An error occurred while processing an update.", exc_info=context.error)

def main():
token = os.getenv("BOT_TOKEN")
if not token:
raise RuntimeError("BOT_TOKEN is missing. Add it to your hosting environment variables.")

```
application = (
    Application.builder()
    .token(token)
    .post_init(post_init)
    .build()
)
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu_command))
application.add_handler(CommandHandler("logout", logout))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess)
)
application.add_error_handler(error_handler)

logger.info("Starting KURO Telegram bot...")
application.run_polling(drop_pending_updates=False)
```

if **name** == "**main**":
main()
