import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Настройки подключения для ЛОКАЛЬНОЙ разработки на компьютере
DB_CONFIG = {
    'dbname': 'ege_db',                 # Имя базы данных
    'user': 'postgres',                 # Пользователь по умолчанию
    'password': '554tyzs_',             # Пароль
    'host': 'localhost',                # Локальный хост
    'port': '5432'                      # Стандартный порт PostgreSQL
}


def get_db():
    """Подключение к базе данных PostgreSQL.
    Автоматически переключается между Render (DATABASE_URL) и локальной БД.
    """
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # Render иногда передает URL с 'postgres://', исправляем на 'postgresql://' для psycopg2
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        # Подключение к локальной базе данных
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        
    return conn


def init_db():
    """Создание и миграция всех необходимых таблиц при старте приложения."""
    conn = get_db()
    cur = conn.cursor()

    try:
        # 1. Таблица пользователей
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT,
                password TEXT,
                goal INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                avatar TEXT,
                reg_date TEXT
            );
        ''')

        # Миграции для подписок и оплаты в таблице пользователей
        cur.execute('''
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS tariff VARCHAR(20) NOT NULL DEFAULT 'simple',
            ADD COLUMN IF NOT EXISTS pro_until TIMESTAMP NULL,
            ADD COLUMN IF NOT EXISTS last_payment_id VARCHAR(100) NULL;
        ''')

        # 2. Таблица задач
        cur.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                number INTEGER,
                source TEXT,
                text TEXT,
                solution TEXT,
                answer TEXT,
                image TEXT
            );
        ''')

        # 3. Связка пользователей и задач
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                status TEXT,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, task_id)
            );
        ''')

        cur.execute('''
            ALTER TABLE user_tasks 
            ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        ''')

        # 4. Таблица теории
        cur.execute('''
            CREATE TABLE IF NOT EXISTS theory_table (
                block_id SERIAL PRIMARY KEY,
                title TEXT,
                task_number INTEGER,
                text TEXT,
                pdf_path TEXT
            );
        ''')

        # 5. Попытки решения задач
        cur.execute('''
            CREATE TABLE IF NOT EXISTS task_attempts (
                id SERIAL PRIMARY KEY,
                task_id INTEGER,
                user_id INTEGER,
                correct INTEGER,
                attempt_number INTEGER
            );
        ''')

        # 6. Варианты
        cur.execute('''
            CREATE TABLE IF NOT EXISTS variants (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                score INTEGER,
                created_at TEXT
            );
        ''')

        cur.execute('''
            ALTER TABLE variants
            ADD COLUMN IF NOT EXISTS name TEXT,
            ADD COLUMN IF NOT EXISTS year INTEGER,
            ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
        ''')

        cur.execute('''
            ALTER TABLE variants
            ALTER COLUMN created_at TYPE TIMESTAMP
            USING (
                CASE
                    WHEN created_at IS NULL THEN CURRENT_TIMESTAMP
                    ELSE created_at::timestamp
                END
            );
        ''')

        # 7. Задачи внутри вариантов
        cur.execute('''
            CREATE TABLE IF NOT EXISTS variant_tasks (
                id SERIAL PRIMARY KEY,
                var_id INTEGER,
                task_id INTEGER,
                task_number INTEGER,
                user_id INTEGER,
                user_answer TEXT,
                correct_answer TEXT,
                correct INTEGER
            );
        ''')

        cur.execute('''
            ALTER TABLE variant_tasks
            ADD COLUMN IF NOT EXISTS position INTEGER DEFAULT 0;
        ''')

        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_user_by_id(user_id: int):
    """Получает пользователя по ID."""
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            SELECT *
            FROM users
            WHERE id = %s
            ''',
            (user_id,)
        )
        user = cur.fetchone()
        return user
    finally:
        cur.close()
        conn.close()


def update_user_pro(user_id: int, pro_until, payment_id: str):
    """Выдаёт пользователю тариф Pro после успешной оплаты."""
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            UPDATE users
            SET
                tariff = 'pro',
                pro_until = %s,
                last_payment_id = %s
            WHERE id = %s
            ''',
            (
                pro_until,
                payment_id,
                user_id
            )
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


# Создаем таблицы при прямом запуске файла
if __name__ == '__main__':
    init_db()
    print("Таблицы базы данных успешно инициализированы в PostgreSQL!")