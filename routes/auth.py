# Регистрация, логин (в т.ч. через Telegram и Google), привязка/отвязка
# соцсетей, профиль, logout

import hashlib
import hmac
import os
import time
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from database import get_db
from decorators import regs_only
from utils import allowed_file, crop, ALLOWED_IMAGES

auth_bp = Blueprint('auth', __name__)

# Токен бота, выданный @BotFather. Храните только в переменной окружения.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Сколько секунд считать данные виджета свежими (защита от повторного использования старой ссылки).
TELEGRAM_AUTH_MAX_AGE = 86400

# Client ID из Google Cloud Console (OAuth client ID, тип Web application).
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')


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


def _unique_username(cur, base):
    """Подбирает свободный логин, отталкиваясь от Telegram/Google username, имени или id."""
    username = base
    suffix = 1

    while True:
        cur.execute('SELECT id FROM users WHERE username = %s', (username,))
        if not cur.fetchone():
            return username
        suffix += 1
        username = f'{base}{suffix}'


def _log_user_in(user):
    """Кладёт данные пользователя в сессию — одинаково для всех способов входа."""
    session['user'] = user['username']
    session['role'] = user['role']
    session['user_id'] = user['id']


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
            return render_template('register.html', error=error, google_client_id=GOOGLE_CLIENT_ID)

        role = 'admin' if username == 'myr' else 'user'
        reg_date = datetime.now().strftime('%d.%m.%Y')
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        cur.execute(
            'INSERT INTO users(username, password, role, reg_date, has_password) VALUES (%s, %s, %s, %s, TRUE)',
            (username, password_hash, role, reg_date)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/login')

    return render_template('register.html', google_client_id=GOOGLE_CLIENT_ID)


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

        _log_user_in(user)

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
            username = _unique_username(cur, base_username)

            reg_date = datetime.now().strftime('%d.%m.%Y')
            # Пароль для входа через Telegram не используется, но поле NOT NULL —
            # сохраняем неиспользуемый hash случайного значения. has_password=FALSE,
            # чтобы позже нельзя было отвязать Telegram без другого способа входа.
            unusable_password = generate_password_hash(os.urandom(32).hex(), method='pbkdf2:sha256')

            cur.execute(
                '''
                INSERT INTO users(username, password, role, reg_date, telegram_id, has_password)
                VALUES (%s, %s, %s, %s, %s, FALSE)
                RETURNING *
                ''',
                (username, unusable_password, 'user', reg_date, telegram_id)
            )
            user = cur.fetchone()
            conn.commit()

        _log_user_in(user)

        return redirect('/')
    finally:
        cur.close()
        conn.close()


# ============================================================
# ЛОГИН ЧЕРЕЗ GOOGLE
# ============================================================
# Кнопка Google Identity Services после успешного входа сама
# отправляет POST-запрос с полем "credential" (ID-токен) прямо
# на этот адрес — см. data-login_uri в register.html.

@auth_bp.route('/login/google', methods=['POST'])
def login_google():
    token = request.form.get('credential')

    if not token or not GOOGLE_CLIENT_ID:
        flash('Не удалось подтвердить вход через Google. Попробуйте ещё раз.')
        return redirect('/login')

    try:
        idinfo = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        flash('Не удалось подтвердить вход через Google. Попробуйте ещё раз.')
        return redirect('/login')

    google_id = idinfo['sub']
    email = idinfo.get('email')

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT * FROM users WHERE google_id = %s', (google_id,))
        user = cur.fetchone()

        if not user and email:
            # Если аккаунт с таким email уже был создан другим способом
            # (логин/пароль или Telegram) — просто привязываем к нему Google,
            # а не плодим дубликат пользователя.
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            if user:
                cur.execute('UPDATE users SET google_id = %s WHERE id = %s', (google_id, user['id']))
                conn.commit()
                cur.execute('SELECT * FROM users WHERE id = %s', (user['id'],))
                user = cur.fetchone()

        if not user:
            base_username = (idinfo.get('name') or (email.split('@')[0] if email else None) or f'google_{google_id}')
            base_username = base_username.strip().replace(' ', '_') or f'google_{google_id}'
            username = _unique_username(cur, base_username)

            reg_date = datetime.now().strftime('%d.%m.%Y')
            # Пароль для входа через Google не используется, но поле NOT NULL —
            # сохраняем неиспользуемый hash случайного значения (как и для Telegram).
            unusable_password = generate_password_hash(os.urandom(32).hex(), method='pbkdf2:sha256')

            cur.execute(
                '''
                INSERT INTO users(username, password, role, reg_date, google_id, email, has_password)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                RETURNING *
                ''',
                (username, unusable_password, 'user', reg_date, google_id, email)
            )
            user = cur.fetchone()
            conn.commit()

        _log_user_in(user)

        return redirect('/')
    finally:
        cur.close()
        conn.close()


# ============================================================
# ПРИВЯЗКА TELEGRAM (из профиля, для уже вошедшего пользователя)
# ============================================================
# Тот же виджет, что и на регистрации, но с другим data-auth-url —
# он не создаёт новую сессию, а привязывает telegram_id к текущему
# session['user_id'].

@auth_bp.route('/link/telegram')
@regs_only
def link_telegram():
    data = request.args.to_dict()

    if not _verify_telegram_auth(data):
        flash('Не удалось подтвердить Telegram. Попробуйте ещё раз.')
        return redirect('/profile')

    telegram_id = data['id']

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT id FROM users WHERE telegram_id = %s', (telegram_id,))
        existing = cur.fetchone()

        if existing and existing['id'] != session['user_id']:
            flash('Этот Telegram-аккаунт уже привязан к другому пользователю.')
            return redirect('/profile')

        cur.execute('UPDATE users SET telegram_id = %s WHERE id = %s', (telegram_id, session['user_id']))
        conn.commit()
        flash('Telegram успешно привязан к аккаунту.')
        return redirect('/profile')
    finally:
        cur.close()
        conn.close()


# ============================================================
# ОТВЯЗКА TELEGRAM
# ============================================================

@auth_bp.route('/unlink/telegram', methods=['POST'])
@regs_only
def unlink_telegram():
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT has_password, google_id FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()

        if not user['has_password'] and not user['google_id']:
            flash('Нельзя отвязать Telegram — это единственный способ входа. Сначала задайте пароль в настройках или привяжите Google.')
            return redirect('/profile')

        cur.execute('UPDATE users SET telegram_id = NULL WHERE id = %s', (session['user_id'],))
        conn.commit()
        flash('Telegram отвязан от аккаунта.')
        return redirect('/profile')
    finally:
        cur.close()
        conn.close()


# ============================================================
# ПРИВЯЗКА GOOGLE (из профиля, для уже вошедшего пользователя)
# ============================================================

@auth_bp.route('/link/google', methods=['POST'])
@regs_only
def link_google():
    token = request.form.get('credential')

    if not token or not GOOGLE_CLIENT_ID:
        flash('Не удалось подтвердить Google. Попробуйте ещё раз.')
        return redirect('/profile')

    try:
        idinfo = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        flash('Не удалось подтвердить Google. Попробуйте ещё раз.')
        return redirect('/profile')

    google_id = idinfo['sub']
    email = idinfo.get('email')

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT id FROM users WHERE google_id = %s', (google_id,))
        existing = cur.fetchone()

        if existing and existing['id'] != session['user_id']:
            flash('Этот Google-аккаунт уже привязан к другому пользователю.')
            return redirect('/profile')

        cur.execute(
            'UPDATE users SET google_id = %s, email = COALESCE(email, %s) WHERE id = %s',
            (google_id, email, session['user_id'])
        )
        conn.commit()
        flash('Google успешно привязан к аккаунту.')
        return redirect('/profile')
    finally:
        cur.close()
        conn.close()


# ============================================================
# ОТВЯЗКА GOOGLE
# ============================================================

@auth_bp.route('/unlink/google', methods=['POST'])
@regs_only
def unlink_google():
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT has_password, telegram_id FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()

        if not user['has_password'] and not user['telegram_id']:
            flash('Нельзя отвязать Google — это единственный способ входа. Сначала задайте пароль в настройках или привяжите Telegram.')
            return redirect('/profile')

        cur.execute('UPDATE users SET google_id = NULL WHERE id = %s', (session['user_id'],))
        conn.commit()
        flash('Google отвязан от аккаунта.')
        return redirect('/profile')
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
    return render_template(
        'profile.html',
        username=session['user'],
        user=user,
        google_client_id=GOOGLE_CLIENT_ID
    )


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
        # Если у пользователя ещё нет настоящего пароля (пришёл через Telegram/Google),
        # проверка старого пароля не имеет смысла — ему просто нечего было вводить.
        if user['has_password'] and not check_password_hash(user['password'], old_password):
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
            'UPDATE users SET password = %s, has_password = TRUE WHERE id = %s',
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