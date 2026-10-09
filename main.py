
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

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
        [
            InlineKeyboardButton("🕵️ Imposter", callback_data="game:imposter"),
        ],
        [
            InlineKeyboardButton("👤 My Profile", callback_data="profile"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
        ],
        [
            InlineKeyboardButton("🚪 Logout", callback_data="logout"),
        ],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
        [InlineKeyboardButton("🚪 Logout", callback_data="logout")],
    ])


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🖤 WELCOME TO KURO\n\n"
        "Your games. Your arena. Your leaderboard.\n\n"
        "🎮 Choose a game from the menu below!"
    )

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=text,
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.effective_message.reply_text(
            text=text,
            reply_markup=main_menu_keyboard(),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_menu(update, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    text = (
        "🚪 KURO session reset.\n\n"
        "Your temporary session data has been cleared.\n"
        "Account login is not enabled in this starter version."
    )

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=text,
            reply_markup=back_keyboard(),
        )
    else:
        await update.effective_message.reply_text(
            text=text,
            reply_markup=back_keyboard(),
        )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "menu":
        await show_menu(update, context)
        return

    if data == "logout":
        await logout(update, context)
        return

    if data.startswith("game:"):
        game_id = data.split(":", 1)[1]
        game = GAMES.get(game_id)

        if game is None:
            await query.edit_message_text(
                "This game was not found.",
                reply_markup=back_keyboard(),
            )
            return

        title, description = game

        await query.edit_message_text(
            f"{title}\n\n"
            f"{description}\n\n"
            "🚧 This game module will be implemented in the next steps.",
            reply_markup=back_keyboard(),
        )
        return

    if data == "profile":
        await query.edit_message_text(
            "👤 MY PROFILE\n\n"
            "Player profiles and statistics will be connected "
            "after the database is configured.",
            reply_markup=back_keyboard(),
        )
        return

    if data == "leaderboard":
        await query.edit_message_text(
            "🏆 LEADERBOARD\n\n"
            "Rankings will appear here after the database and "
            "game scoring system are implemented.",
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
        BotCommand("logout", "Reset your temporary session"),
    ])
    logger.info("KURO bot commands registered.")


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
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
    application.add_error_handler(error_handler)

    logger.info("Starting KURO Telegram bot...")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
