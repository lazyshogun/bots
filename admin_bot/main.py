import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
from common.db import get_user  # И другие функции по необходимости

load_dotenv()

TELEGRAM_TOKEN_ADMIN = os.getenv("TELEGRAM_TOKEN_ADMIN")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Добро пожаловать в админ-бот. Здесь можно управлять пользователями, вопросами и промптами.")

def main():
    updater = Updater(TELEGRAM_TOKEN_ADMIN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
