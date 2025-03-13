import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
from common.db import get_user, get_questions, get_prompt

load_dotenv()  # Загружаем переменные окружения из .env

TELEGRAM_TOKEN_CLIENT = os.getenv("TELEGRAM_TOKEN_CLIENT")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    if not user:
        update.message.reply_text("Вы не авторизованы. Обратитесь к администратору.")
        return

    business_type = user["business_type"]
    questions = get_questions(business_type)
    prompt = get_prompt(business_type)

    if not questions:
        update.message.reply_text("Ошибка: для вашего типа бизнеса не найдены вопросы. Обратитесь к администратору.")
        return

    if not prompt:
        update.message.reply_text("Ошибка: для вашего типа бизнеса не найден промпт. Обратитесь к администратору.")
        return

    # Здесь можно продолжить логику анкеты; для примера просто выводим загруженные данные
    update.message.reply_text(
        f"Добро пожаловать!\nВаш тип бизнеса: {business_type}\n\n"
        f"Вопросы для анкеты:\n{chr(10).join(questions)}\n\n"
        f"Промпт для генерации отзыва:\n{prompt}"
    )

def main():
    updater = Updater(TELEGRAM_TOKEN_CLIENT, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
