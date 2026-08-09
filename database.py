# Подключение к БД, функции-хелперы и init_db()

import sqlite3
DATABASE = 'users.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            goal INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user',
            avatar TEXT,
            reg_date TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY,
            number INTEGER,
            source TEXT,
            text TEXT,
            solution TEXT,
            answer TEXT,
            image TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            status TEXT,
            UNIQUE(user_id,task_id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS theory_table(
            block_id INTEGER PRIMARY KEY,
            title TEXT,
            task_number INTEGER,
            text TEXT,
            pdf_path TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS task_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            user_id INTEGER,
            correct INTEGER,
            attempt_number INTEGER
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER,
            created_at TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS variant_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            var_id INTEGER,
            task_id INTEGER,
            task_number INTEGER,
            user_id INTEGER,
            user_answer TEXT,
            correct_answer TEXT,
            correct INTEGER
        )
    ''')
    conn.commit()
    conn.close()