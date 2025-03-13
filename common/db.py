# common/db.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Загружаем переменные окружения из .env (локально)
# или из Railway Variables (в продакшене)
load_dotenv()

# Читаем параметры подключения к PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mybotdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

def get_db_connection():
    """
    Создает и возвращает соединение с базой данных PostgreSQL.
    """
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

def get_user(telegram_id: int):
    """
    Возвращает запись о пользователе из таблицы users по полю telegram_id.
    Если пользователь не найден, возвращает None.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT *
                FROM users
                WHERE telegram_id = %s
                LIMIT 1
            """
            cur.execute(query, (telegram_id,))
            user = cur.fetchone()
            return user
    finally:
        conn.close()

def get_questions(business_type: str):
    """
    Возвращает список вопросов (question_text) для указанного business_type
    из таблицы questions. Если ничего не найдено, возвращает пустой список.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT question_text
                FROM questions
                WHERE business_type = %s
                ORDER BY id
            """
            cur.execute(query, (business_type,))
            rows = cur.fetchall()
            questions = [row["question_text"] for row in rows]
            return questions
    finally:
        conn.close()

def get_prompt(business_type: str):
    """
    Возвращает промпт (prompt_text) для указанного business_type
    из таблицы prompts. Если запись не найдена, возвращает None.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT prompt_text
                FROM prompts
                WHERE business_type = %s
                LIMIT 1
            """
            cur.execute(query, (business_type,))
            row = cur.fetchone()
            return row["prompt_text"] if row else None
    finally:
        conn.close()
