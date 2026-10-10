import asyncio
import logging
import os
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from games.number_game import create_game

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

DIFFICULTIES = {
    4: {"name": "EASY", "solo_attempts": 15, "multi_attempts": 20},
    5: {"name": "MEDIUM", "solo_attempts": 20, "multi_attempts": 25},
    6: {"name": "HARD", "solo_attempts": 25, "multi_attempts": 30},
    7: {"name": "EXPERT", "solo_attempts": 30, "multi_attempts": 35},
}
LOBBY_SECONDS = 90
MIN_PLAYERS = 2
MAX_PLAYERS = 10
SIMULTANEOUS_WIN_WINDOW = 0.35


def format_guess_feedback(secret, guess, attempts_left, attempts_label="Attempts remaining"):
    """Show the submitted digits and one color signal beneath each digit."""
    signals = []
    for secret_digit, guessed_digit in zip(str(secret), str(guess)):
        if guessed_digit == secret_digit:
            signals.append("🟢")
        elif guessed_digit in str(secret):
            signals.append("🟡")
        else:
            signals.append("🔴")

    digits_line = "  ".join(str(guess))
    signals_line = "  ".join(signals)
    return (
        f"🔢 {digits_line}\n"
        f"{signals_line}\n\n"
        f"❤️ {attempts_label}: {attempts_left}"
    )


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


def mode_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Solo", callback_data="number:mode:solo"),
            InlineKeyboardButton("👥 Multiplayer", callback_data="number:mode:multi"),
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
        [InlineKeyboardButton("🚪 Logout", callback_data="logout")],
    ])


def difficulty_keyboard(mode):
    is_multi = mode == "multi"
    rows = []
    for digits, difficulty in DIFFICULTIES.items():
        attempts = difficulty["multi_attempts"] if is_multi else difficulty["solo_attempts"]
        label = f"{difficulty['name'].title()} — {digits} digits ({attempts} attempts)"
        rows.append([
            InlineKeyboardButton(
                label,
                callback_data=f"number:start:{mode}:{digits}",
            )
        ])
    rows.extend([
        [InlineKeyboardButton("⬅️ Choose Mode", callback_data="game:number")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
        [InlineKeyboardButton("🚪 Logout", callback_data="logout")],
    ])
    return InlineKeyboardMarkup(rows)


def game_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Play Again", callback_data="game:number")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
        [InlineKeyboardButton("🚪 Logout", callback_data="logout")],
    ])


def join_keyboard():
    # This is a shared group message, so only provide the join action.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Game", callback_data="number:join")],
    ])


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🖤 WELCOME TO KURO\n\n"
        "Your games. Your arena. Your leaderboard.\n\n"
        "🎮 Choose a game from the menu below!"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text, reply_markup=main_menu_keyboard()
        )
    else:
        await update.effective_message.reply_text(
            text, reply_markup=main_menu_keyboard()
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    context.application.bot_data.setdefault("solo_games", {}).pop((chat_id, user_id), None)
    await show_menu(update, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    context.application.bot_data.setdefault("solo_games", {}).pop((chat_id, user_id), None)
    text = (
        "🚪 KURO session reset.\n\n"
        "Your Solo game session has been cleared. Any shared Multiplayer match "
        "continues for its joined players.\n"
        "Account login is not enabled in this version."
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=back_keyboard())
    else:
        await update.effective_message.reply_text(text, reply_markup=back_keyboard())


def is_group_chat(chat):
    return chat is not None and chat.type in ("group", "supergroup")


def player_name(user):
    # Telegram display name only; never use @username.
    return user.full_name or "Player"


def lobby_text(lobby):
    elapsed = time.monotonic() - lobby["created_at"]
    remaining = max(0, int(LOBBY_SECONDS - elapsed + 0.999))
    difficulty = DIFFICULTIES[lobby["digits"]]["name"]
    names = "\n".join(
        f"{index}. {player['name']}"
        for index, player in enumerate(lobby["players"].values(), start=1)
    )
    return (
        f"👥 KURO MULTIPLAYER LOBBY — {difficulty}\n\n"
        f"🔢 Combination: {lobby['digits']} unique digits\n"
        f"👤 Players ({len(lobby['players'])}/{MAX_PLAYERS}):\n"
        f"{names}\n\n"
        f"⏳ Starts in: {remaining} seconds\n"
        "Tap Join Game to enter. The creator is already joined."
    )


async def begin_number_solo(update, context, digits):
    difficulty = DIFFICULTIES[digits]
    attempts = difficulty["solo_attempts"]
    game = create_game(digits=digits, attempts=attempts)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    context.application.bot_data.setdefault("solo_games", {})[(chat_id, user_id)] = game

    await update.callback_query.edit_message_text(
        f"🔢 NUMBER COMBINATION — {difficulty['name']}\n\n"
        f"I've picked a secret {digits}-digit combination with no repeated digits.\n"
        f"You have {attempts} attempts to crack it.\n\n"
        "🟢 Correct digit and position  ·  🟡 Digit exists, wrong position  ·  🔴 Digit absent\n"
        "⚠️ Leading zeroes are allowed.",
        reply_markup=back_keyboard(),
    )


async def begin_multiplayer_lobby(update, context, digits):
    chat = update.effective_chat
    user = update.effective_user

    if not is_group_chat(chat):
        await update.callback_query.edit_message_text(
            "👥 Multiplayer is designed for a Telegram group.\n\n"
            "Add KURO to your group, open its menu there, and start Multiplayer.",
            reply_markup=back_keyboard(),
        )
        return

    existing_game = context.application.bot_data.setdefault("multiplayer_games", {}).get(chat.id)
    if existing_game and not existing_game.get("finished"):
        await update.callback_query.edit_message_text(
            "⚠️ A Multiplayer match is already running in this group.\n"
            "Finish that match before starting another one.",
            reply_markup=back_keyboard(),
        )
        return

    existing_lobby = context.application.bot_data.setdefault("multiplayer_lobbies", {}).get(chat.id)
    if existing_lobby and existing_lobby.get("status") == "waiting":
        await update.callback_query.edit_message_text(
            "⚠️ A Multiplayer lobby is already open in this group.",
            reply_markup=back_keyboard(),
        )
        return

    lobby = {
        "chat_id": chat.id,
        "message_id": update.callback_query.message.message_id,
        "creator_id": user.id,
        "digits": digits,
        "created_at": time.monotonic(),
        "status": "waiting",
        "players": {user.id: {"id": user.id, "name": player_name(user)}},
    }
    context.application.bot_data["multiplayer_lobbies"][chat.id] = lobby

    await update.callback_query.edit_message_text(
        lobby_text(lobby),
        reply_markup=join_keyboard(),
    )
    context.application.create_task(
        lobby_countdown(context.application, chat.id),
        name=f"kuro-lobby-{chat.id}",
    )


async def start_multiplayer_game(application, chat_id, lobby):
    if lobby.get("status") != "waiting":
        return
    if len(lobby["players"]) < MIN_PLAYERS:
        return

    lobby["status"] = "started"
    difficulty = DIFFICULTIES[lobby["digits"]]
    attempts = difficulty["multi_attempts"]
    game = create_game(digits=lobby["digits"], attempts=attempts)
    game.update({
        "chat_id": chat_id,
        "digits": lobby["digits"],
        "attempts_left": attempts,
        "max_attempts": attempts,
        "players": dict(lobby["players"]),
        "finished": False,
        "resolving": False,
        "pending_winners": [],
        "lobby_message_id": lobby["message_id"],
    })
    application.bot_data.setdefault("multiplayer_games", {})[chat_id] = game

    names = "\n".join(f"• {p['name']}" for p in game["players"].values())
    text = (
        f"🎮 MULTIPLAYER MATCH STARTED — {difficulty['name']}\n\n"
        f"👥 Players ({len(game['players'])}/{MAX_PLAYERS}):\n{names}\n\n"
        f"🔢 Secret combination: {game['digits']} unique digits\n"
        f"❤️ Collective attempts: {attempts}\n\n"
        "All joined players share the same attempt pool. Each valid guess uses "
        "one attempt. First correct guess wins; near-simultaneous correct guesses "
        "within a brief race window can share the win.\n\n"
        "🟢 Correct position  ·  🟡 Present, wrong position  ·  🔴 Not in the combination"
    )
    try:
        await application.bot.edit_message_text(
            chat_id=chat_id,
            message_id=lobby["message_id"],
            text=text,
            reply_markup=None,
        )
    except TelegramError:
        logger.exception("Could not update lobby message when match started.")
        await application.bot.send_message(chat_id=chat_id, text=text)


async def lobby_countdown(application, chat_id):
    while True:
        await asyncio.sleep(5)
        lobby = application.bot_data.get("multiplayer_lobbies", {}).get(chat_id)
        if not lobby or lobby.get("status") != "waiting":
            return

        elapsed = time.monotonic() - lobby["created_at"]
        remaining = LOBBY_SECONDS - elapsed
        if remaining <= 0:
            if len(lobby["players"]) >= MIN_PLAYERS:
                await start_multiplayer_game(application, chat_id, lobby)
            else:
                lobby["status"] = "cancelled"
                try:
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=lobby["message_id"],
                        text=(
                            "⌛ Multiplayer lobby closed because at least 2 players "
                            "did not join within 90 seconds.\n\nStart a new match when "
                            "your group is ready."
                        ),
                        reply_markup=back_keyboard(),
                    )
                except TelegramError:
                    logger.exception("Could not update expired lobby.")
            return

        try:
            await application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=lobby["message_id"],
                text=lobby_text(lobby),
                reply_markup=join_keyboard(),
            )
        except TelegramError:
            logger.debug("Lobby countdown message update skipped.", exc_info=True)


async def handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat = query.message.chat
    user = query.from_user
    if not is_group_chat(chat):
        await query.answer("Multiplayer joining is only available in groups.", show_alert=True)
        return

    lobby = context.application.bot_data.setdefault("multiplayer_lobbies", {}).get(chat.id)
    if (
        not lobby
        or lobby.get("status") != "waiting"
        or lobby.get("message_id") != query.message.message_id
    ):
        await query.answer("This lobby is no longer open.", show_alert=True)
        return

    if user.id in lobby["players"]:
        await query.answer("You're already in this lobby.")
        return

    if len(lobby["players"]) >= MAX_PLAYERS:
        await query.answer("This lobby is full.", show_alert=True)
        return

    if user.is_bot:
        await query.answer("Bots cannot join a match.", show_alert=True)
        return

    lobby["players"][user.id] = {"id": user.id, "name": player_name(user)}
    await query.answer("Joined KURO Multiplayer!")
    if len(lobby["players"]) >= MAX_PLAYERS:
        await start_multiplayer_game(context.application, chat.id, lobby)
        return

    try:
        await query.edit_message_text(lobby_text(lobby), reply_markup=join_keyboard())
    except TelegramError:
        logger.exception("Could not refresh lobby after a player joined.")


async def finish_multiplayer_winner(application, chat_id):
    await asyncio.sleep(SIMULTANEOUS_WIN_WINDOW)
    game = application.bot_data.get("multiplayer_games", {}).get(chat_id)
    if not game or game.get("finished"):
        return
    winners = game.get("pending_winners", [])
    if not winners:
        game["resolving"] = False
        return

    game["finished"] = True
    game["resolving"] = False
    winner_names = " + ".join(winner["name"] for winner in winners)
    title = "🏆 WINNER!" if len(winners) == 1 else "🏆 JOINT WINNERS!"
    await application.bot.send_message(
        chat_id=chat_id,
        text=(
            f"{title}\n\n"
            f"🎉 {winner_names}\n"
            f"🔢 Secret combination: {game['secret']}\n"
            f"❤️ Collective attempts remaining: {game['attempts_left']}\n\n"
            "The match is over. Use /start to open KURO and start another match."
        ),
    )


async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not user or not chat or not message.text:
        return

    bot_data = context.application.bot_data
    multiplayer = bot_data.setdefault("multiplayer_games", {}).get(chat.id)

    # Once a group match has ended, later guesses must not fall through into Solo.
    if is_group_chat(chat) and multiplayer and multiplayer.get("finished"):
        return

    # A live group match takes priority; only players who joined can spend attempts.
    if is_group_chat(chat) and multiplayer and not multiplayer.get("finished"):
        if user.id not in multiplayer["players"]:
            return
        if multiplayer.get("resolving"):
            guess = message.text.strip()
            if (
                guess == multiplayer["secret"]
                and user.id not in {p["id"] for p in multiplayer["pending_winners"]}
            ):
                multiplayer["pending_winners"].append({"id": user.id, "name": player_name(user)})
            return

        guess = message.text.strip()
        digits = multiplayer["digits"]
        if not guess.isdigit() or len(guess) != digits or len(set(guess)) != digits:
            await message.reply_text(
                f"{player_name(user)}, enter exactly {digits} digits with no repeats."
            )
            return

        multiplayer["attempts_left"] -= 1
        feedback = format_guess_feedback(
            multiplayer["secret"], guess, multiplayer["attempts_left"],
            attempts_label="Collective attempts remaining",
        )
        if guess == multiplayer["secret"]:
            multiplayer["resolving"] = True
            multiplayer["pending_winners"] = [{"id": user.id, "name": player_name(user)}]
            await message.reply_text(f"👤 {player_name(user)}\n{feedback}\n\n🏆 Correct combination!")
            context.application.create_task(
                finish_multiplayer_winner(context.application, chat.id),
                name=f"kuro-winner-{chat.id}",
            )
            return

        if multiplayer["attempts_left"] <= 0:
            multiplayer["finished"] = True
            await message.reply_text(
                f"👤 {player_name(user)}\n{feedback}\n\n"
                "❌ MULTIPLAYER GAME OVER!\n"
                f"Secret combination: {multiplayer['secret']}"
            )
            return

        await message.reply_text(f"👤 {player_name(user)}\n{feedback}")
        return

    solo = bot_data.setdefault("solo_games", {}).get((chat.id, user.id))
    if not solo or solo.get("finished"):
        return

    guess = message.text.strip()
    digits = solo["digits"]
    if not guess.isdigit() or len(guess) != digits or len(set(guess)) != digits:
        await message.reply_text(
            f"Please enter exactly {digits} different digits (no repeats)."
        )
        return

    solo["attempts_left"] -= 1
    secret = solo["secret"]
    feedback = format_guess_feedback(secret, guess, solo["attempts_left"])
    if guess == secret:
        solo["finished"] = True
        used = solo["max_attempts"] - solo["attempts_left"]
        await message.reply_text(
            f"{feedback}\n\n🎉 YOU CRACKED IT!\n"
            f"Attempts used: {used}",
            reply_markup=game_keyboard(),
        )
        return

    if solo["attempts_left"] <= 0:
        solo["finished"] = True
        await message.reply_text(
            f"{feedback}\n\n❌ GAME OVER!\n"
            f"The secret combination was: {secret}",
            reply_markup=game_keyboard(),
        )
        return

    await message.reply_text(feedback)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    if data != "number:join":
        await query.answer()

    if data == "menu":
        await show_menu(update, context)
        return

    if data == "logout":
        await logout(update, context)
        return

    if data == "game:number":
        await query.edit_message_text(
            "🔢 NUMBER COMBINATION\n\nChoose how you want to play:",
            reply_markup=mode_keyboard(),
        )
        return

    if data == "number:mode:solo":
        await query.edit_message_text(
            "👤 SOLO MODE\n\nChoose your difficulty:",
            reply_markup=difficulty_keyboard("solo"),
        )
        return

    if data == "number:mode:multi":
        if not is_group_chat(query.message.chat):
            await query.edit_message_text(
                "👥 Multiplayer is designed for a Telegram group.\n\n"
                "Add KURO to your group, open its menu there, and start Multiplayer.",
                reply_markup=back_keyboard(),
            )
            return
        await query.edit_message_text(
            "👥 MULTIPLAYER MODE\n\n"
            "Choose difficulty. The lobby will accept 2–10 players for up to 90 seconds.",
            reply_markup=difficulty_keyboard("multi"),
        )
        return

    if data == "number:join":
        await handle_join(update, context)
        return

    if data.startswith("number:start:"):
        try:
            _, _, mode, digits_text = data.split(":")
            digits = int(digits_text)
            if mode not in ("solo", "multi") or digits not in DIFFICULTIES:
                raise ValueError("Unsupported difficulty")
            if mode == "solo":
                await begin_number_solo(update, context, digits)
            else:
                await begin_multiplayer_lobby(update, context, digits)
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
            await query.edit_message_text("Game not found.", reply_markup=back_keyboard())
        return

    if data == "profile":
        await query.edit_message_text(
            "👤 MY PROFILE\n\n"
            "Profiles and statistics will be connected after database setup.",
            reply_markup=back_keyboard(),
        )
        return

    if data == "leaderboard":
        await query.edit_message_text(
            "🏆 LEADERBOARD\n\n"
            "Rankings will appear after database and scoring setup.",
            reply_markup=back_keyboard(),
        )
        return

    await query.edit_message_text(
        "Unknown option. Please return to the main menu.",
        reply_markup=back_keyboard(),
    )


async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Open KURO"),
        BotCommand("menu", "Show the main menu"),
        BotCommand("logout", "Reset your Solo session"),
    ])
    logger.info("KURO bot commands registered.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(
        "An error occurred while processing an update.",
        exc_info=context.error,
    )


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is missing. Add it to your hosting environment variables."
        )

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
    application.add_error_handler(error_handler)

    logger.info("Starting KURO Telegram bot...")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
