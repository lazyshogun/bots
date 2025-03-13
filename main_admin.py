import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from config import TELEGRAM_ADMIN_TOKEN, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    return conn

# Пример команды /adduser
def add_user(update: Update, context: CallbackContext):
    # Ожидается: /adduser telegram_id business_type
    try:
        telegram_id = int(context.args[0])
        business_type = context.args[1]
    except (IndexError, ValueError):
        update.message.reply_text("Используйте: /adduser <telegram_id> <business_type>")
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (telegram_id, business_type) VALUES (%s, %s) ON CONFLICT (telegram_id) DO NOTHING", (telegram_id, business_type))
            conn.commit()
        update.message.reply_text("Пользователь добавлен.")
    except Exception as e:
        logger.error(e)
        update.message.reply_text("Ошибка при добавлении пользователя.")
    finally:
        conn.close()

def main():
    updater = Updater(TELEGRAM_ADMIN_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("adduser", add_user))
    # Добавьте другие команды для управления вопросами и промптами аналогичным образом.
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
