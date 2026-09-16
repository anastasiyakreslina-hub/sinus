# =========================================================
# TASKS — БАНК ЗАДАЧ
# =========================================================

import os

from flask import Blueprint, flash, redirect, render_template, request, session
from werkzeug.utils import secure_filename

from database import get_db
from decorators import admin_only, regs_only
from utils import ALLOWED_IMAGES, allowed_file
from helpers.task_stats import get_first_attempt_stats, record_attempt


tasks_bp = Blueprint('tasks', __name__)


# Границы сложности по проценту решивших с первой попытки.
# Задачи без единой попытки (pct is None) ни в одну категорию не попадают.
DIFFICULTY_RANGES = {
    'easy':   lambda pct: pct >= 70,
    'medium': lambda pct: 40 <= pct < 70,
    'hard':   lambda pct: pct < 40,
}


@tasks_bp.route('/tasks')
@regs_only
def tasks():
    user_id = session.get('user_id')
    number = request.args.get('number')
    task_id = request.args.get('task_id')
    difficulty = request.args.get('difficulty')

    conn = get_db()
    cur = conn.cursor()

    try:
        query = '''
            SELECT tasks.*, COALESCE(user_tasks.status, 'Задача еще не решена') AS status
            FROM tasks
            LEFT JOIN user_tasks ON tasks.id = user_tasks.task_id AND user_tasks.user_id = %s
            WHERE 1=1
        '''
        options = [user_id]

        if number:
            query += ' AND tasks.number = %s'
            options.append(number)

        if task_id:
            query += ' AND tasks.id = %s'
            options.append(task_id)

        query += ' ORDER BY tasks.id'

        cur.execute(query, options)
        tasks_list = cur.fetchall()
        stats = get_first_attempt_stats(cur)

        if difficulty in DIFFICULTY_RANGES:
            check = DIFFICULTY_RANGES[difficulty]
            tasks_list = [
                task for task in tasks_list
                if stats.get(task['id']) is not None and check(stats[task['id']])
            ]

        return render_template('tasks.html', tasks=tasks_list, stats=stats)
    finally:
        cur.close()
        conn.close()


@tasks_bp.route('/add_task', methods=['POST'])
@admin_only
def add_task():
    number = request.form['number']
    source = request.form['source']
    text = request.form['text']
    solution = request.form['solution']
    answer = request.form['answer']
    image = request.files.get('image')

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            'INSERT INTO tasks(number, source, text, solution, answer) VALUES(%s, %s, %s, %s, %s) RETURNING id',
            (number, source, text, solution, answer)
        )
        task_id = cur.fetchone()['id']

        if image and image.filename != '':
            if not allowed_file(image.filename, ALLOWED_IMAGES):
                flash('Упс! Неверный формат изображения!')
                return redirect('/profile')

            safe_fname = secure_filename(image.filename)
            ext = safe_fname.rsplit('.', 1)[1].lower() if '.' in safe_fname else 'png'
            image_name = f'task_{task_id}.{ext}'
            folder = os.path.join('static', 'task_images')

            os.makedirs(folder, exist_ok=True)
            image.save(os.path.join(folder, image_name))

            cur.execute('UPDATE tasks SET image = %s WHERE id = %s', (f'task_images/{image_name}', task_id))

        conn.commit()
        return redirect('/tasks')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@tasks_bp.route('/edit_task/<int:task_id>', methods=['POST'])
@admin_only
def edit_task(task_id):
    number = request.form['number']
    source = request.form['source']
    text = request.form['text']
    solution = request.form['solution']
    answer = request.form['answer']

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            'UPDATE tasks SET number = %s, source = %s, text = %s, solution = %s, answer = %s WHERE id = %s',
            (number, source, text, solution, answer, task_id)
        )
        conn.commit()
        return redirect('/tasks')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@tasks_bp.route('/delete_task/<int:task_id>', methods=['POST'])
@admin_only
def delete_task(task_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
        conn.commit()
        return redirect('/tasks')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@tasks_bp.route('/check_answer/<int:task_id>', methods=['POST'])
def check_answer(task_id):
    data = request.get_json() or {}
    user_answer = data.get('answer', '')
    user_id = session.get('user_id')

    if user_id is None:
        return {'result': 'red', 'text': 'Сначала войдите в аккаунт'}

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT answer FROM tasks WHERE id = %s', (task_id,))
        correct = cur.fetchone()

        if correct is None:
            return {'result': 'red', 'text': 'Задача не найдена'}

        is_correct = int(user_answer.strip() == correct['answer'].strip())
        status = 'Правильно!' if is_correct else 'Неправильно!'
        result = 'correct' if is_correct else 'wrong'

        attempt_number = record_attempt(cur, user_id, task_id, is_correct)
        conn.commit()

        return {'result': result, 'text': status, 'attempt_number': attempt_number}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@tasks_bp.route('/mistakes')
@regs_only
def mistakes():
    user_id = session.get('user_id')

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('''
            SELECT tasks.*
            FROM tasks
            JOIN user_tasks ON tasks.id = user_tasks.task_id
            WHERE user_tasks.user_id = %s AND user_tasks.status = 'Неправильно!'
            ORDER BY tasks.id
        ''', (user_id,))
        tasks_list = cur.fetchall()

        stats = get_first_attempt_stats(cur)

        return render_template('mistakes.html', tasks=tasks_list, stats=stats)
    finally:
        cur.close()
        conn.close()