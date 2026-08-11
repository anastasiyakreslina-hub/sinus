# Вспомогательные функции (crop, allowed_file, подсчет статистики)

from database import get_db

ALLOWED_IMAGES = {'png', 'jpg', 'jpeg'}
ALLOWED_PDFS = {'pdf'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def crop(img):
    width, height = img.size
    target = 4 / 5
    current = width / height
    if current > target:
        new_width = int(height * target)
        left = (width - new_width) // 2
        img = img.crop((left, 0, left + new_width, height))
    else:
        new_height = int(width / target)
        top = (height - new_height) // 2
        img = img.crop((0, top, width, top + new_height))
    return img

def all_count(user_id):
    conn = get_db()
    cur = conn.cursor()
    # ? заменен на %s, добавлен alias для ключа count
    cur.execute('SELECT COUNT(*) AS total FROM user_tasks WHERE user_id = %s', (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['total'] if row else 0

def correct_count(user_id):
    conn = get_db()
    cur = conn.cursor()
    # ? заменен на %s, двойные кавычки заменены на одинарные
    cur.execute("SELECT COUNT(*) AS total FROM user_tasks WHERE user_id = %s AND status LIKE 'Правильно%%'", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['total'] if row else 0

def get_goal(username):
    conn = get_db()
    cur = conn.cursor()
    # ? заменен на %s, обращение по ключу 'goal'
    cur.execute('SELECT goal FROM users WHERE username = %s', (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['goal'] if row and row['goal'] is not None else 0