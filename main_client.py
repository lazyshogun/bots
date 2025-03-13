import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import openai
import urllib.parse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
)
from config import TELEGRAM_CLIENT_TOKEN, OPENAI_API_KEY, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Настройка OpenAI API
openai.api_key = OPENAI_API_KEY

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем состояния диалога
START_MENU, QUESTION, CONFIRM_REVIEW, EDIT_REVIEW_STATE = range(4)

# Функция для подключения к БД
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

# Проверка пользователя по Telegram ID
def get_user(telegram_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM users WHERE telegram_id = %s LIMIT 1"
            cur.execute(query, (telegram_id,))
            return cur.fetchone()
    finally:
        conn.close()

# Загрузка вопросов для заданного business_type
def get_questions(business_type: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT question_text FROM questions WHERE business_type = %s ORDER BY id"
            cur.execute(query, (business_type,))
            rows = cur.fetchall()
            return [row["question_text"] for row in rows]
    finally:
        conn.close()

# Загрузка промпта для заданного business_type
def get_prompt(business_type: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT prompt_text FROM prompts WHERE business_type = %s LIMIT 1"
            cur.execute(query, (business_type,))
            row = cur.fetchone()
            return row["prompt_text"] if row else None
    finally:
        conn.close()

# --- Стартовое меню ---
def start(update: Update, context: CallbackContext) -> int:
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    if not user:
        update.message.reply_text("Вы не авторизованы. Обратитесь к администратору.")
        return ConversationHandler.END

    # Пользователь найден – получаем его бизнес-группу
    business_type = user["business_type"]
    # Загружаем вопросы и промпт для данного типа бизнеса
    questions = get_questions(business_type)
    prompt = get_prompt(business_type)

    if not questions:
        update.message.reply_text("Ошибка: для вашего типа бизнеса не найдены вопросы. Обратитесь к администратору.")
        return ConversationHandler.END

    if not prompt:
        update.message.reply_text("Ошибка: для вашего типа бизнеса не найден промпт. Обратитесь к администратору.")
        return ConversationHandler.END

    # Сохраняем данные в user_data для дальнейшей работы
    context.user_data["business_type"] = business_type
    context.user_data["questions"] = questions
    context.user_data["prompt"] = prompt
    context.user_data["current_question"] = 0
    context.user_data["answers"] = []

    # Показываем стартовое меню анкеты
    keyboard = [
        [InlineKeyboardButton("✅ Начать анкетирование", callback_data="start_survey")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=reply_markup)
    return START_MENU

def start_menu_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == "start_survey":
        # Начинаем с первого вопроса
        questions = context.user_data["questions"]
        question_text = f"📝 Вопрос 1/4:\n{questions[0]}"
        query.edit_message_text(text=question_text)
        return QUESTION
    elif query.data == "cancel":
        query.edit_message_text(text="Анкетирование отменено.")
        return ConversationHandler.END

# --- Этап вопросов ---
def answer_handler(update: Update, context: CallbackContext) -> int:
    current_q = context.user_data.get("current_question", 0)
    answer = update.message.text
    answers = context.user_data.get("answers", [])
    if len(answers) > current_q:
        answers[current_q] = answer
    else:
        answers.append(answer)
    context.user_data["answers"] = answers

    keyboard = [
        [
            InlineKeyboardButton("🔄 Изменить ответ", callback_data="edit_answer"),
            InlineKeyboardButton("⏭ Далее", callback_data="next_question"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"Ответ: \"{answer}\"\nВыберите действие:", reply_markup=reply_markup)
    return QUESTION

def question_callback_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    current_q = context.user_data.get("current_question", 0)
    questions = context.user_data["questions"]
    if query.data == "edit_answer":
        query.edit_message_text(text=f"📝 Вопрос {current_q+1}/4:\n{questions[current_q]}\nВведите новый ответ:")
        return QUESTION
    elif query.data == "next_question":
        current_q += 1
        context.user_data["current_question"] = current_q
        if current_q < len(questions):
            question_text = f"📝 Вопрос {current_q+1}/4:\n{questions[current_q]}"
            query.edit_message_text(text=question_text)
            return QUESTION
        else:
            # Все вопросы заданы – формируем промпт
            answers = context.user_data["answers"]
            prompt = context.user_data["prompt"]
            dynamic_prompt = "На основе следующих ответов составь отзыв для клиники:\n\n"
            for i, ans in enumerate(answers):
                dynamic_prompt += f"{i+1}. {ans}\n"
            dynamic_prompt += "\n" + prompt

            query.edit_message_text(text="Формирую отзыв, пожалуйста, подождите...")
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",  # При необходимости замените на нужную модель
                    messages=[
                        {"role": "system", "content": "Ты помогаешь составить отзыв на клинику."},
                        {"role": "user", "content": dynamic_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                generated_review = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Ошибка при вызове OpenAI API: {e}")
                query.edit_message_text(text="Ошибка генерации отзыва. Попробуйте позже.")
                return ConversationHandler.END

            context.user_data["generated_review"] = generated_review
            keyboard = [
                [
                    InlineKeyboardButton("✏️ Отредактировать отзыв", callback_data="edit_review"),
                    InlineKeyboardButton("✅ Отправить в WhatsApp", callback_data="send_whatsapp"),
                    InlineKeyboardButton("🔄 Начать заново", callback_data="restart"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            review_text = f"🎉 Отзыв сформирован:\n\"{generated_review}\""
            query.edit_message_text(text=review_text, reply_markup=reply_markup)
            return CONFIRM_REVIEW
    else:
        query.edit_message_text(text="Неизвестная команда, завершаем диалог.")
        return ConversationHandler.END

# --- Этап подтверждения отзыва ---
def review_callback_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == "edit_review":
        keyboard = [[InlineKeyboardButton("Назад", callback_data="cancel_edit")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text="Введите отредактированный отзыв или нажмите 'Назад' для отмены редактирования:",
            reply_markup=reply_markup
        )
        return EDIT_REVIEW_STATE
    elif query.data == "send_whatsapp":
        review = context.user_data.get("generated_review", "")
        encoded_text = urllib.parse.quote(review)
        whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"
        keyboard = [
            [InlineKeyboardButton("Открыть WhatsApp", url=whatsapp_url)],
            [
                InlineKeyboardButton("Назад", callback_data="back_from_whatsapp"),
                InlineKeyboardButton("Отредактировать отзыв", callback_data="edit_review"),
                InlineKeyboardButton("🔄 Начать заново", callback_data="restart"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text="Отправьте отзыв через WhatsApp или выберите другое действие:",
            reply_markup=reply_markup,
        )
        return CONFIRM_REVIEW
    elif query.data == "back_from_whatsapp":
        generated_review = context.user_data.get("generated_review", "")
        keyboard = [
            [
                InlineKeyboardButton("✏️ Отредактировать отзыв", callback_data="edit_review"),
                InlineKeyboardButton("✅ Отправить в WhatsApp", callback_data="send_whatsapp"),
                InlineKeyboardButton("🔄 Начать заново", callback_data="restart"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=f"🎉 Отзыв сформирован:\n\"{generated_review}\"", reply_markup=reply_markup)
        return CONFIRM_REVIEW
    elif query.data == "restart":
        # Очищаем данные и отправляем новое стартовое меню
        context.user_data.clear()
        keyboard = [
            [InlineKeyboardButton("✅ Начать анкетирование", callback_data="start_survey")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="📌 Выберите действие:", reply_markup=reply_markup)
        return START_MENU
    else:
        query.edit_message_text(text="Неизвестная команда, завершаем диалог.")
        return ConversationHandler.END

def edit_review_handler(update: Update, context: CallbackContext) -> int:
    edited_review = update.message.text
    context.user_data["generated_review"] = edited_review
    keyboard = [
        [
            InlineKeyboardButton("✏️ Отредактировать отзыв", callback_data="edit_review"),
            InlineKeyboardButton("✅ Отправить в WhatsApp", callback_data="send_whatsapp"),
            InlineKeyboardButton("🔄 Начать заново", callback_data="restart"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"Ваш отредактированный отзыв:\n\"{edited_review}\"\nВыберите действие:", reply_markup=reply_markup)
    return CONFIRM_REVIEW

def cancel_edit_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    generated_review = context.user_data.get("generated_review", "")
    keyboard = [
        [
            InlineKeyboardButton("✏️ Отредактировать отзыв", callback_data="edit_review"),
            InlineKeyboardButton("✅ Отправить в WhatsApp", callback_data="send_whatsapp"),
            InlineKeyboardButton("🔄 Начать заново", callback_data="restart"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=f"Отзыв сохранён:\n\"{generated_review}\"", reply_markup=reply_markup)
    return CONFIRM_REVIEW

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Диалог отменен.")
    return ConversationHandler.END

def main():
    updater = Updater(TELEGRAM_CLIENT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_MENU: [CallbackQueryHandler(start_menu_handler, pattern="^(start_survey|cancel)$")],
            QUESTION: [
                MessageHandler(Filters.text & ~Filters.command, answer_handler),
                CallbackQueryHandler(question_callback_handler, pattern="^(edit_answer|next_question)$"),
            ],
            CONFIRM_REVIEW: [
                CallbackQueryHandler(review_callback_handler, pattern="^(edit_review|send_whatsapp|back_from_whatsapp|restart)$"),
                MessageHandler(Filters.text & ~Filters.command, edit_review_handler),
            ],
            EDIT_REVIEW_STATE: [
                CallbackQueryHandler(cancel_edit_handler, pattern="^cancel_edit$"),
                MessageHandler(Filters.text & ~Filters.command, edit_review_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
