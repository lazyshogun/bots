import os

# Токены ботов
TELEGRAM_CLIENT_TOKEN = os.environ.get("TELEGRAM_CLIENT_TOKEN")  # для клиентского бота
TELEGRAM_ADMIN_TOKEN = os.environ.get("TELEGRAM_ADMIN_TOKEN")    # для админ-бота

# Ключ OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Параметры подключения к PostgreSQL
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

