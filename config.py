import os

# Токены ботов
TELEGRAM_TOKEN_ADMIN = os.getenv("TELEGRAM_TOKEN_ADMIN")
TELEGRAM_TOKEN_CLIENT = os.getenv("TELEGRAM_TOKEN_CLIENT")

# Доступ к базе данных
DB_HOST = os.getenv("PGHOST")
DB_PORT = os.getenv("PGPORT")
DB_NAME = os.getenv("PGDATABASE")
DB_USER = os.getenv("PGUSER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
