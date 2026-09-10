# Регистрация, логин (в т.ч. через Telegram), профиль, logout

import hashlib
import hmac
import os
import time
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image

from database import get_db
from decorators import regs_only
from utils import allowed_file, crop, ALLOWED_IMAGES

auth_bp = Blueprint('auth', __name__)

# Токен бота, выданный @BotFather. Храните только в переменной окружения.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Сколько секунд считать данные виджета свежими (защита от повторного использования старой ссылки).
TELEGRAM_AUTH_MAX_AGE = 86400


# ============================================================
# TELEGRAM LOGIN — ПРОВЕРКА ПОДПИСИ
# ============================================================

def _verify_telegram_auth(data):
    """
    Проверяет, что данные действительно пришли от Telegram.
    См. https://core.telegram.org/widgets/login#checking-authorization
    """
    if not TELEGRAM_BOT_TOKEN:
        return False

    data = dict(data)
    received_hash = data.pop('hash', None)
    if not received_hash:
        return False

    check_string = '\n'.join(f'{k}={data[k]}' for k in sorted(data.keys()))
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return False

    auth_date = int(data.get('auth_date', 0))
    if time.time() - auth_date > TELEGRAM_AUTH_MAX_AGE:
        return False

    return True


def _unique_telegram_username(cur, base):
    """Подбирает свободный логин, отталкиваясь от Telegram username / имени / id."""
    username = base
    suffix = 1

    while True:
        cur.execute('SELECT id FROM users WHERE username = %s', (username,))
        if not cur.fetchone():
            return username
        suffix += 1
        username = f'{base}{suffix}'


# ============================================================
# РЕГИСТРАЦИЯ
# ============================================================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()

        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            error = 'Упс! Этот логин уже занят'
            return render_template('register.html', error=error)

        role = 'admin' if username == 'myr' else 'user'
        reg_date = datetime.now().strftime('%d.%m.%Y')
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        cur.execute(
            'INSERT INTO users(username, password, role, reg_date) VALUES (%s, %s, %s, %s)',
            (username, password_hash, role, reg_date)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/login')

    return render_template('register.html')


# ============================================================
# ЛОГИН (ЛОГИН + ПАРОЛЬ)
# ============================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()

        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()

        if not user:
            error = 'Упс! Неверный логин или пароль'
            cur.close()
            conn.close()
            return render_template('login.html', error=error)

        # Старые аккаунты с паролем в открытом виде — мигрируем на hash при первом входе.
        if not str(user['password']).startswith('pbkdf2:'):
            if user['password'] != password:
                error = 'Упс! Неверный логин или пароль'
                cur.close()
                conn.close()
                return render_template('login.html', error=error)

            new_hash = generate_password_hash(password, method='pbkdf2:sha256')
            cur.execute('UPDATE users SET password = %s WHERE id = %s', (new_hash, user['id']))
            conn.commit()
        elif not check_password_hash(user['password'], password):
            error = 'Упс! Неверный логин или пароль'
            cur.close()
            conn.close()
            return render_template('login.html', error=error)

        session['user'] = user['username']
        session['role'] = user['role']
        session['user_id'] = user['id']

        cur.close()
        conn.close()
        return redirect('/')

    return render_template('login.html', error=error)


# ============================================================
# ЛОГИН ЧЕРЕЗ TELEGRAM
# ============================================================
# Виджет Telegram после входа делает GET-редирект на этот адрес
# с параметрами id, first_name, last_name, username, photo_url,
# auth_date и hash. См. шаги настройки в ответе ассистента.

@auth_bp.route('/login/telegram')
def login_telegram():
    data = request.args.to_dict()

    if not _verify_telegram_auth(data):
        flash('Не удалось подтвердить вход через Telegram. Попробуйте ещё раз.')
        return redirect('/login')

    telegram_id = data['id']

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT * FROM users WHERE telegram_id = %s', (telegram_id,))
        user = cur.fetchone()

        if not user:
            base_username = (data.get('username') or data.get('first_name') or f'tg_{telegram_id}').strip()
            base_username = base_username.replace(' ', '_') or f'tg_{telegram_id}'
            username = _unique_telegram_username(cur, base_username)

            reg_date = datetime.now().strftime('%d.%m.%Y')
            # Пароль для входа через Telegram не используется, но поле NOT NULL —
            # сохраняем неиспользуемый hash случайного значения.
            unusable_password = generate_password_hash(os.urandom(32).hex(), method='pbkdf2:sha256')

            cur.execute(
                '''
                INSERT INTO users(username, password, role, reg_date, telegram_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                ''',
                (username, unusable_password, 'user', reg_date, telegram_id)
            )
            user = cur.fetchone()
            conn.commit()

        session['user'] = user['username']
        session['role'] = user['role']
        session['user_id'] = user['id']

        return redirect('/')
    finally:
        cur.close()
        conn.close()


# ============================================================
# ПРОФИЛЬ
# ============================================================

@auth_bp.route('/profile', methods=['GET', 'POST'])
@regs_only
def profile():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        goal = request.form['goal']
        cur.execute('UPDATE users SET goal = %s WHERE id = %s', (goal, session['user_id']))
        conn.commit()

    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()

    cur.close()
    conn.close()
    return render_template('profile.html', username=session['user'], user=user)


@auth_bp.route('/change_profile', methods=['POST'])
@regs_only
def change_profile():
    conn = get_db()
    cur = conn.cursor()

    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()

    username = request.form['username'].strip()
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    repeat_password = request.form['repeat_password']

    if username != user['username']:
        cur.execute('SELECT id FROM users WHERE username = %s', (username,))
        if cur.fetchone():
            flash('Упс! Такой логин уже существует!')
            cur.close()
            conn.close()
            return redirect('/profile')

        cur.execute('UPDATE users SET username = %s WHERE id = %s', (username, session['user_id']))
        session['user'] = username

    if new_password:
        if not check_password_hash(user['password'], old_password):
            flash('Упс! Неверный пароль!')
            cur.close()
            conn.close()
            return redirect('/profile')

        if new_password != repeat_password:
            flash('Упс! Пароли не совпадают')
            cur.close()
            conn.close()
            return redirect('/profile')

        if session.get('user') == 'testacc':
            flash('Упс! Это тестовый аккаунт')
            cur.close()
            conn.close()
            return redirect('/profile')

        cur.execute(
            'UPDATE users SET password = %s WHERE id = %s',
            (generate_password_hash(new_password, method='pbkdf2:sha256'), session['user_id'])
        )

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/profile')


# ============================================================
# АВАТАР
# ============================================================

@auth_bp.route('/upload_avatar', methods=['POST'])
@regs_only
def upload_avatar():
    file = request.files.get('avatar')

    if not file or file.filename == '':
        return redirect('/profile')

    if not allowed_file(file.filename, ALLOWED_IMAGES):
        return 'Выберите изображение формата png, jpg или jpeg'

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'user_{session["user_id"]}.{ext}'
    path = os.path.join('static', 'avatars', filename)
    base = f'user_{session["user_id"]}'

    for old_ext in ALLOWED_IMAGES:
        old_path = os.path.join('static', 'avatars', f'{base}.{old_ext}')
        if os.path.exists(old_path):
            os.remove(old_path)

    img = crop(Image.open(file))
    new_width = 250
    ratio = new_width / img.width
    new_height = int(img.height * ratio)
    img = img.resize((new_width, new_height))
    img.save(path)

    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE users SET avatar = %s WHERE id = %s', (f'avatars/{filename}', session['user_id']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/profile')


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')