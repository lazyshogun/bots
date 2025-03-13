import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters
import openai
from config import TELEGRAM_TOKEN, OPENAI_API_KEY, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Настройка OpenAI API
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Функция для подключения к базе данных
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

# Проверка пользователя по telegram_id
def get_user(telegram_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE telegram_id = %s LIMIT 1", (telegram_id,))
            user = cur.fetchone()
            return user
    finally:
        conn.close()

# Загрузка списка вопросов для заданного business_type
def get_questions(business_type: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT question_text FROM questions WHERE business_type = %s ORDER BY id", (business_type,))
            rows = cur.fetchall()
            questions = [row["question_text"] for row in rows]
            return questions
    finally:
        conn.close()

# Загрузка промпта для заданного business_type
def get_prompt(business_type: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT prompt_text FROM prompts WHERE business_type = %s LIMIT 1", (business_type,))
            row = cur.fetchone()
            return row["prompt_text"] if row else None
    finally:
        conn.close()

# Определяем состояние разговора (для простоты здесь один этап)
STATE = 1

# Обработчик команды /start
def start_command(update: Update, context: CallbackContext) -> int:
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    if not user:
        update.message.reply_text("Вы не авторизованы. Обратитесь к администратору.")
        return ConversationHandler.END

    business_type = user["business_type"]
    questions = get_questions(business_type)
    prompt = get_prompt(business_type)

    if not questions:
        update.message.reply_text("Ошибка: для вашего типа бизнеса не найдены вопросы. Обратитесь к администратору.")
        return ConversationHandler.END

    if not prompt:
        update.message.reply_text("Ошибка: для вашего типа бизнеса не найден промпт. Обратитесь к администратору.")
        return ConversationHandler.END

    # Сохраняем данные в context
    context.user_data["business_type"] = business_type
    context.user_data["questions"] = questions
    context.user_data["prompt"] = prompt

    # Выводим приветственное сообщение с загруженными данными
    update.message.reply_text(
        f"Добро пожаловать!\nВаш тип бизнеса: {business_type}\n\n"
        f"Вопросы для анкеты:\n{chr(10).join(questions)}\n\n"
        f"Промпт для генерации отзыва:\n{prompt}"
    )
    # Здесь дальше можно добавить логику проведения опроса
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Диалог отменен.")
    return ConversationHandler.END

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            STATE: [MessageHandler(Filters.text & ~Filters.command, start_command)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
