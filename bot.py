import os
import logging
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
)

from database import init_db
from handlers import (
    start, help_command, today, favorite, favorites,
    quiz, review, button_callback
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is required")

    init_db()
    logger.info("Database initialized")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("favorite", favorite))
    app.add_handler(CommandHandler("favorites", favorites))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("review", review))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
