import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from config import TELEGRAM_TOKEN, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def add_user(update: Update, context: CallbackContext):
    # Пример команды: /adduser 123456789 business1
    try:
        telegram_id = int(context.args[0])
        business_type = context.args[1]
    except (IndexError, ValueError):
        update.message.reply_text("Используйте: /adduser telegram_id business_type")
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (telegram_id, business_type) VALUES (%s, %s) ON CONFLICT (telegram_id) DO UPDATE SET business_type = EXCLUDED.business_type", (telegram_id, business_type))
            conn.commit()
            update.message.reply_text("Пользователь добавлен или обновлён.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        update.message.reply_text("Ошибка при добавлении пользователя.")
    finally:
        conn.close()

def add_question(update: Update, context: CallbackContext):
    # Пример команды: /addquestion business1 "Какой у вас опыт работы?"
    try:
        business_type = context.args[0]
        question_text = " ".join(context.args[1:])
    except IndexError:
        update.message.reply_text("Используйте: /addquestion business_type вопрос")
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO questions (business_type, question_text) VALUES (%s, %s)", (business_type, question_text))
            conn.commit()
            update.message.reply_text("Вопрос добавлен.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении вопроса: {e}")
        update.message.reply_text("Ошибка при добавлении вопроса.")
    finally:
        conn.close()

def add_prompt(update: Update, context: CallbackContext):
    # Пример команды: /addprompt business1 "Составь отзыв, основываясь на следующих ответах..."
    try:
        business_type = context.args[0]
        prompt_text = " ".join(context.args[1:])
    except IndexError:
        update.message.reply_text("Используйте: /addprompt business_type prompt_text")
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO prompts (business_type, prompt_text) VALUES (%s, %s) ON CONFLICT (business_type) DO UPDATE SET prompt_text = EXCLUDED.prompt_text", (business_type, prompt_text))
            conn.commit()
            update.message.reply_text("Промпт добавлен или обновлён.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении промпта: {e}")
        update.message.reply_text("Ошибка при добавлении промпта.")
    finally:
        conn.close()

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("adduser", add_user))
    dp.add_handler(CommandHandler("addquestion", add_question))
    dp.add_handler(CommandHandler("addprompt", add_prompt))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
