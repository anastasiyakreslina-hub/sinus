# Регистрация, логин, профиль, logout

import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image

from database import get_db
from decorators import regs_only
from utils import allowed_file, crop, ALLOWED_IMAGES

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        # Заменен ? на %s
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        if user:
            cur.close()
            conn.close()
            error = 'Упс! Этот логин уже занят'
            return render_template('register.html', error=error)
        role = 'admin' if username == 'myr' else 'user'
        reg_date = datetime.now().strftime('%d.%m.%Y')
        password = generate_password_hash(password, method='pbkdf2:sha256')
        # Заменены ? на %s
        cur.execute('INSERT INTO users(username, password, role, reg_date) VALUES (%s, %s, %s, %s)', 
                    (username, password, role, reg_date))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        # Заменен ? на %s
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        if user:
            if not str(user['password']).startswith('pbkdf2:'):
                if user['password'] == password:
                    new_hash = generate_password_hash(password, method='pbkdf2:sha256')
                    # Заменены ? на %s
                    cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, user['id']))
                    conn.commit()
                    session['user'] = username
                    session['role'] = user['role']
                    session['user_id'] = user['id']
                    cur.close()
                    conn.close()
                    return redirect('/')
                else:
                    error = 'Упс! Неверный логин или пароль'
            else:
                if check_password_hash(user['password'], password):
                    session['user'] = username
                    session['role'] = user['role']
                    session['user_id'] = user['id']
                    cur.close()
                    conn.close()
                    return redirect('/')
                else:
                    error = 'Упс! Неверный логин или пароль'
        else:
            error = 'Упс! Неверный логин или пароль'
            cur.close()
            conn.close()
            return render_template('login.html', error=error)
        cur.close()
        conn.close()
    return render_template('login.html', error=error)

@auth_bp.route('/profile', methods=['GET', 'POST'])
@regs_only
def profile():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        goal = request.form['goal']
        # Заменены ? на %s
        cur.execute('UPDATE users SET goal = %s WHERE id = %s', (goal, session['user_id']))
        conn.commit()
    # Заменен ? на %s
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
    # Заменен ? на %s
    cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cur.fetchone()
    username = request.form['username'].strip()
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    repeat_password = request.form['repeat_password']
    
    if username != user['username']:
        # Заменен ? на %s
        cur.execute('SELECT id FROM users WHERE username = %s', (username,))
        if cur.fetchone():
            flash('Упс! Такой логин уже существует!')
            cur.close()
            conn.close()
            return redirect('/profile')
        # Заменены ? на %s
        cur.execute('UPDATE users SET username = %s WHERE id = %s', (username, session["user_id"]))
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
        # Заменены ? на %s
        cur.execute('UPDATE users SET password = %s WHERE id = %s', 
                    (generate_password_hash(new_password, method='pbkdf2:sha256'), session['user_id']))

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/profile')

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
    
    for old in ALLOWED_IMAGES:
        old_path = os.path.join('static', 'avatars', f'{base}.{old}')
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
    # Заменены ? на %s
    cur.execute('UPDATE users SET avatar = %s WHERE id = %s', (f'avatars/{filename}', session['user_id']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/profile')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')