# Подключение к БД, функции-хелперы и init_db() для PostgreSQL

import psycopg2
from psycopg2.extras import RealDictCursor

# Настройки подключения к базе данных PostgreSQL
# ⚠️ Укажите ваш реальный пароль от пользователя postgres вместо 'ваш_пароль_postgres'
DB_CONFIG = {
    'dbname': 'ege_db',                 # Имя базы данных, созданной в pgAdmin
    'user': 'postgres',                 # Пользователь по умолчанию
    'password': '554tyzs_',  # Пароль, заданный при установке PostgreSQL
    'host': 'localhost',                # Локальный хост
    'port': '5432'                      # Стандартный порт PostgreSQL
}


def get_db():
    """Подключение к базе данных PostgreSQL.
    Возвращает подключение с курсором RealDictCursor (возврат строк в виде словарей).
    """
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    return conn


def init_db():
    """Создание всех необходимых таблиц при старте приложения"""
    conn = get_db()
    cur = conn.cursor()

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

    # 3. Связка пользователей и задач (статусы решения + дата выполнения)
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

    # Гарантированное добавление столбца completed_at, если таблица user_tasks уже существовала ранее
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

    # 7. Задачи внутри созданных вариантов
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

    conn.commit()
    cur.close()
    conn.close()


# Создаем таблицы при запуске/импорте файла
if __name__ == '__main__':
    init_db()
    print("Таблицы базы данных успешно инициализированы в PostgreSQL!")