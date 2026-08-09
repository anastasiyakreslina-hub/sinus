# Задачи, варианты, проверка ответов

import os
import random
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, flash

from database import get_db
from decorators import admin_only, regs_only
from utils import allowed_file, ALLOWED_IMAGES, all_count, correct_count

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/tasks')
@regs_only
def tasks():
    user_id = session.get('user_id')
    number = request.args.get('number')
    task_id = request.args.get('task_id')
    conn = get_db()
    cur = conn.cursor()
    query = '''
        SELECT tasks.*, COALESCE(user_tasks.status,'Задача еще не решена') AS status FROM tasks
        LEFT JOIN user_tasks
        ON tasks.id=user_tasks.task_id AND user_tasks.user_id=?
        WHERE 1=1
    '''
    options = [user_id]
    if number:
        query += ' AND tasks.number=?'
        options.append(number)
    if task_id:
        query += ' AND tasks.id=?'
        options.append(task_id)
    cur.execute(query, options)
    tasks_list = cur.fetchall()

    cur.execute('''
        SELECT task_id, COUNT(*) AS total, SUM(CASE WHEN attempt_number=1 AND correct=1 THEN 1 ELSE 0 END) AS correct_first_attempts
        FROM task_attempts
        GROUP BY task_id
    ''')
    stats_raw = cur.fetchall()
    stats = {}
    for r in stats_raw:
        t_id = r['task_id']
        total = r[1]
        first_attempts = r[2]
        percent = (first_attempts / total) * 100 if total > 0 else 0
        stats[t_id] = round(percent, 2)
    conn.close()
    return render_template('tasks.html', tasks=tasks_list, stats=stats)

@tasks_bp.route('/add_task', methods=['POST'])
@admin_only
def add_task():
    number = request.form['number']
    source = request.form['source']
    text = request.form['text']
    solution = request.form['solution']
    image = request.files.get('image')
    answer = request.form['answer']
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO tasks(number, source, text, solution, answer) VALUES(?,?,?,?,?)',
        (number, source, text, solution, answer)
    )
    task_id = cur.lastrowid
    if image and image.filename != '':
        if not allowed_file(image.filename, ALLOWED_IMAGES):
            flash('Упс! Неверный формат изображения!')
            conn.close()
            return redirect('/profile')
        ext = image.filename.rsplit('.', 1)[1].lower()
        image_name = f'task_{task_id}.{ext}'
        folder = os.path.join('static', 'task_images')
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, image_name)
        image.save(path)
        cur.execute('UPDATE tasks SET image=? WHERE id=?', (f'task_images/{image_name}', task_id))
    conn.commit()
    conn.close()
    return redirect('/tasks')

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
    cur.execute(
        'UPDATE tasks SET number=?, source=?, text=?, solution=?, answer=? WHERE id=?',
        (number, source, text, solution, answer, task_id)
    )
    conn.commit()
    conn.close()
    return redirect('/tasks')

@tasks_bp.route('/delete_task/<int:task_id>', methods=['POST'])
@admin_only
def delete_task(task_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM tasks WHERE id=?', (task_id,))
    conn.commit()
    conn.close()
    return redirect('/tasks')

@tasks_bp.route('/check_answer/<int:task_id>', methods=['POST'])
def check_answer(task_id):
    data = request.get_json() or {}
    user_answer = data.get('answer', '')
    user_id = session.get('user_id')
    if user_id is None:
        return {'result': 'red', 'text': 'Сначала войдите в аккаунт'}
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT answer FROM tasks WHERE id=?', (task_id,))
    correct = cur.fetchone()
    if correct is None:
        conn.close()
        return {'result': 'red', 'text': 'задача не найдена'}
    is_correct = int(user_answer.strip() == correct[0].strip())
    status = 'Правильно!' if is_correct else 'Неправильно!'
    result = 'correct' if is_correct else 'wrong'
    
    cur.execute('SELECT COUNT(*) FROM task_attempts WHERE user_id=? AND task_id=?', (user_id, task_id))
    attempt_number = cur.fetchone()[0] + 1
    cur.execute(
        'INSERT INTO task_attempts(user_id,task_id,correct,attempt_number) VALUES(?,?,?,?)',
        (user_id, task_id, is_correct, attempt_number)
    )
    cur.execute('''
        INSERT INTO user_tasks(user_id,task_id,status) VALUES(?,?,?)
        ON CONFLICT(user_id, task_id) DO UPDATE SET status=excluded.status
    ''', (user_id, task_id, status))
    conn.commit()
    conn.close()
    return {'result': result, 'text': status, 'attempt_number': attempt_number}

@tasks_bp.route('/mistakes')
@regs_only
def mistakes():
    user_id = session.get('user_id')
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT tasks.* FROM tasks 
        JOIN user_tasks ON tasks.id=user_tasks.task_id 
        WHERE user_tasks.user_id=? AND user_tasks.status="Неправильно!"
    ''', (user_id,))
    tasks_list = cur.fetchall()
    conn.close()
    return render_template('mistakes.html', tasks=tasks_list)

@tasks_bp.route('/tests')
@regs_only
def tests():
    return render_template('tests.html')

@tasks_bp.route('/generate_var')
@regs_only
def generate_var():
    conn = get_db()
    cur = conn.cursor()
    var_tasks = []
    nums = list(range(1, 20))
    for number in nums:
        cur.execute('SELECT * FROM tasks WHERE number=?', (number,))
        t_list = cur.fetchall()
        if t_list:
            var_tasks.append(random.choice(t_list))
    conn.close()
    return render_template('var.html', var_tasks=var_tasks)

@tasks_bp.route('/check_var', methods=['POST'])
@regs_only
def check_var():
    conn = get_db()
    cur = conn.cursor()
    task_ids = request.form.getlist('task_id')
    score = 0
    answers = []
    for task_id in task_ids:
        cur.execute('SELECT * FROM tasks WHERE id=?', (task_id,))
        task = cur.fetchone()
        user_answer = request.form.get(f'answer_{task_id}', '').strip()
        correct = task['answer'].strip()
        is_correct = int(user_answer == correct)
        if is_correct:
            score += 1
        answers.append({
            'task_id': task_id,
            'task_number': task['number'],
            'user_answer': user_answer,
            'correct_answer': correct,
            'correct': is_correct
        })
    cur.execute('INSERT INTO variants(user_id, score, created_at) VALUES(?,?,?)',
                (session['user_id'], score, datetime.now().strftime("%d.%m.%Y %H:%M")))
    var_id = cur.lastrowid
    for ans in answers:
        cur.execute('''
            INSERT INTO variant_tasks(var_id, task_id, task_number, user_id, user_answer, correct_answer, correct)
            VALUES(?,?,?,?,?,?,?)
        ''', (var_id, ans['task_id'], ans['task_number'], session['user_id'], ans['user_answer'], ans['correct_answer'], ans['correct']))
    conn.commit()
    conn.close()
    return {'score': score, 'total': len(task_ids)}

@tasks_bp.route('/statistics')
@regs_only
def statistics():
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id=?', (user_id,))
    user = cur.fetchone()
    solved_count = all_count(user_id)
    correct = correct_count(user_id)
    goal = user['goal']
    percent = int((correct / solved_count) * 100) if solved_count else 0
    
    cur.execute('''
        SELECT tasks.number, ROUND(100*SUM(CASE WHEN user_tasks.status LIKE 'Правильно!' THEN 1 ELSE 0 END)/COUNT(*), 1) AS percent
        FROM user_tasks JOIN tasks ON user_tasks.task_id=tasks.id 
        WHERE user_tasks.user_id=?
        GROUP BY tasks.number ORDER BY tasks.number 
    ''', (user_id,))
    data = cur.fetchall()
    numbers = [row['number'] for row in data]
    percents = [row['percent'] for row in data]

    cur.execute('''
        SELECT tasks.number, COUNT(*) AS total, SUM(CASE WHEN task_attempts.attempt_number=1 AND task_attempts.correct=1 THEN 1 ELSE 0 END) AS correct_first_attempts
        FROM task_attempts JOIN tasks ON tasks.id=task_attempts.task_id
        WHERE task_attempts.user_id=?
        GROUP BY tasks.number ORDER BY tasks.number
    ''', (user_id,))
    raw = cur.fetchall()
    first_attempts_numbers = []
    first_attempts_percents = []
    for r in raw:
        num = r['number']
        tot = r['total']
        first = r['correct_first_attempts']
        p_first = (first / tot) * 100 if tot > 0 else 0
        first_attempts_numbers.append(num)
        first_attempts_percents.append(round(p_first, 2))

    cur.execute('''
        SELECT 
            variant_tasks.var_id, tasks.number AS task_number, variant_tasks.task_id,
            variant_tasks.user_answer, variant_tasks.correct_answer, variant_tasks.correct,
            variants.score, variants.created_at
        FROM variant_tasks
        JOIN variants ON variant_tasks.var_id=variants.id
        JOIN tasks ON variant_tasks.task_id=tasks.id
        WHERE variants.user_id=?
        ORDER BY variant_tasks.var_id, tasks.number
    ''', (user_id,))
    variant_data = cur.fetchall()
    variant_table = {}
    for row in variant_data:
        var_id = row['var_id']
        if var_id not in variant_table:
            variant_table[var_id] = {
                'score': row['score'],
                'created_at': row['created_at'],
                'tasks': {}
            }
        variant_table[var_id]['tasks'][row['task_number']] = {
            'task_id': row['task_id'],
            'answer': row['user_answer'],
            'correct_answer': row['correct_answer'],
            'correct': row['correct']
        }
    conn.close()
    return render_template(
        'statistics.html', user=user, solved_count=solved_count, correct=correct,
        goal=goal, percent=percent, numbers=numbers, percents=percents,
        first_attempts_numbers=first_attempts_numbers,
        first_attempts_percents=first_attempts_percents,
        variant_table=variant_table
    )