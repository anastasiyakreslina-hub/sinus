# =========================================================
# ЗАДАЧИ, ВАРИАНТЫ, ПРОВЕРКА ОТВЕТОВ
# =========================================================

import os
import random
from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)
from werkzeug.utils import secure_filename

from database import get_db
from decorators import admin_only, regs_only
from utils import ALLOWED_IMAGES, all_count, allowed_file, correct_count


tasks_bp = Blueprint('tasks', __name__)


# =========================================================
# TASKS — БАНК ЗАДАЧ
# =========================================================

@tasks_bp.route('/tasks')
@regs_only
def tasks():
    user_id = session.get('user_id')
    number = request.args.get('number')
    task_id = request.args.get('task_id')

    conn = get_db()
    cur = conn.cursor()

    try:
        query = '''
            SELECT
                tasks.*,
                COALESCE(
                    user_tasks.status,
                    'Задача еще не решена'
                ) AS status
            FROM tasks
            LEFT JOIN user_tasks
                ON tasks.id = user_tasks.task_id
                AND user_tasks.user_id = %s
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

        # Статистика первой попытки
        cur.execute('''
            SELECT
                task_id,
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN attempt_number = 1 AND correct = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS correct_first_attempts
            FROM task_attempts
            GROUP BY task_id
        ''')

        stats_raw = cur.fetchall()
        stats = {}

        for r in stats_raw:
            t_id = r['task_id']
            total = r['total'] or 0
            first_attempts = r['correct_first_attempts'] or 0

            percent = (first_attempts / total * 100) if total > 0 else 0
            stats[t_id] = round(percent, 2)

        return render_template(
            'tasks.html',
            tasks=tasks_list,
            stats=stats
        )
    finally:
        cur.close()
        conn.close()


# =========================================================
# ADD TASK
# =========================================================

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
            '''
            INSERT INTO tasks(number, source, text, solution, answer)
            VALUES(%s, %s, %s, %s, %s)
            RETURNING id
            ''',
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
            path = os.path.join(folder, image_name)
            image.save(path)

            cur.execute(
                '''
                UPDATE tasks
                SET image = %s
                WHERE id = %s
                ''',
                (f'task_images/{image_name}', task_id)
            )

        conn.commit()
        return redirect('/tasks')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================================================
# EDIT TASK
# =========================================================

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
            '''
            UPDATE tasks
            SET
                number = %s,
                source = %s,
                text = %s,
                solution = %s,
                answer = %s
            WHERE id = %s
            ''',
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


# =========================================================
# DELETE TASK
# =========================================================

@tasks_bp.route('/delete_task/<int:task_id>', methods=['POST'])
@admin_only
def delete_task(task_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            DELETE FROM tasks
            WHERE id = %s
            ''',
            (task_id,)
        )

        conn.commit()
        return redirect('/tasks')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================================================
# CHECK SINGLE TASK
# =========================================================

@tasks_bp.route('/check_answer/<int:task_id>', methods=['POST'])
def check_answer(task_id):
    data = request.get_json() or {}
    user_answer = data.get('answer', '')
    user_id = session.get('user_id')

    if user_id is None:
        return {
            'result': 'red',
            'text': 'Сначала войдите в аккаунт'
        }

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            SELECT answer
            FROM tasks
            WHERE id = %s
            ''',
            (task_id,)
        )

        correct = cur.fetchone()

        if correct is None:
            return {
                'result': 'red',
                'text': 'Задача не найдена'
            }

        is_correct = int(user_answer.strip() == correct['answer'].strip())
        status = 'Правильно!' if is_correct else 'Неправильно!'
        result = 'correct' if is_correct else 'wrong'

        # Номер попытки
        cur.execute(
            '''
            SELECT COUNT(*) AS total
            FROM task_attempts
            WHERE user_id = %s AND task_id = %s
            ''',
            (user_id, task_id)
        )

        attempt_number = cur.fetchone()['total'] + 1

        # Записываем попытку
        cur.execute(
            '''
            INSERT INTO task_attempts(user_id, task_id, correct, attempt_number)
            VALUES(%s, %s, %s, %s)
            ''',
            (user_id, task_id, is_correct, attempt_number)
        )

        # Обновляем статус
        cur.execute(
            '''
            INSERT INTO user_tasks(user_id, task_id, status, completed_at)
            VALUES(%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, task_id)
            DO UPDATE SET
                status = EXCLUDED.status,
                completed_at = CURRENT_TIMESTAMP
            ''',
            (user_id, task_id, status)
        )

        conn.commit()

        return {
            'result': result,
            'text': status,
            'attempt_number': attempt_number
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================================================
# MISTAKES
# =========================================================

@tasks_bp.route('/mistakes')
@regs_only
def mistakes():
    user_id = session.get('user_id')

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            SELECT tasks.*
            FROM tasks
            JOIN user_tasks
                ON tasks.id = user_tasks.task_id
            WHERE user_tasks.user_id = %s
              AND user_tasks.status = 'Неправильно!'
            ORDER BY tasks.id
            ''',
            (user_id,)
        )

        tasks_list = cur.fetchall()

        # Статистика
        cur.execute('''
            SELECT
                task_id,
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN attempt_number = 1 AND correct = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS correct_first_attempts
            FROM task_attempts
            GROUP BY task_id
        ''')

        stats_raw = cur.fetchall()
        stats = {}

        for r in stats_raw:
            t_id = r['task_id']
            total = r['total'] or 0
            first_attempts = r['correct_first_attempts'] or 0

            percent = (first_attempts / total * 100) if total > 0 else 0
            stats[t_id] = round(percent, 2)

        return render_template(
            'mistakes.html',
            tasks=tasks_list,
            stats=stats
        )
    finally:
        cur.close()
        conn.close()


# =========================================================
# ВАРИАНТЫ
# =========================================================

@tasks_bp.route('/tests')
@regs_only
def tests():
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            SELECT id, name, year, created_at
            FROM variants
            WHERE is_public = TRUE
            ORDER BY year DESC, created_at DESC, id DESC
            '''
        )

        variants = cur.fetchall()

        years = {}
        for variant in variants:
            year = variant['year']
            if year not in years:
                years[year] = []
            years[year].append(variant)

        return render_template('tests.html', years=years)
    finally:
        cur.close()
        conn.close()


# =========================================================
# АДМИН: ДОБАВИТЬ ГОТОВЫЙ ВАРИАНТ
# =========================================================

@tasks_bp.route('/add_variant', methods=['POST'])
@admin_only
def add_variant():
    name = request.form.get('name', '').strip()
    year = request.form.get('year', '').strip()
    task_ids_text = request.form.get('task_ids', '').strip()

    if not name:
        flash('Введите название варианта')
        return redirect('/tests')

    try:
        year = int(year)
    except (TypeError, ValueError):
        flash('Введите корректный год')
        return redirect('/tests')

    raw_ids = task_ids_text.replace(';', ',').split(',')
    task_ids = []

    for value in raw_ids:
        value = value.strip()
        if not value:
            continue

        try:
            task_id = int(value)
        except ValueError:
            flash(f'Некорректный ID задания: {value}')
            return redirect('/tests')

        if task_id not in task_ids:
            task_ids.append(task_id)

    if not task_ids:
        flash('Добавьте хотя бы одно задание')
        return redirect('/tests')

    conn = get_db()
    cur = conn.cursor()

    try:
        placeholders = ','.join(['%s'] * len(task_ids))
        cur.execute(
            f'''
            SELECT id
            FROM tasks
            WHERE id IN ({placeholders})
            ''',
            tuple(task_ids)
        )

        existing_ids = {row['id'] for row in cur.fetchall()}
        missing_ids = [t_id for t_id in task_ids if t_id not in existing_ids]

        if missing_ids:
            flash('Не найдены задания: ' + ', '.join(map(str, missing_ids)))
            return redirect('/tests')

        cur.execute(
            '''
            INSERT INTO variants(user_id, score, created_at, name, year, is_public)
            VALUES(NULL, NULL, %s, %s, %s, TRUE)
            RETURNING id
            ''',
            (datetime.now(), name, year)
        )

        var_id = cur.fetchone()['id']

        for task_id in task_ids:
            cur.execute(
                '''
                INSERT INTO variant_tasks(
                    var_id, task_id, task_number, user_id, user_answer, correct_answer, correct
                )
                SELECT %s, id, number, NULL, NULL, answer, NULL
                FROM tasks
                WHERE id = %s
                ''',
                (var_id, task_id)
            )

        conn.commit()

        flash('Вариант успешно добавлен!')
        return redirect('/tests')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================================================
# ПРОСМОТР ГОТОВОГО ВАРИАНТА
# =========================================================

@tasks_bp.route('/variant/<int:variant_id>')
@regs_only
def view_variant(variant_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            SELECT id, name, year, created_at
            FROM variants
            WHERE id = %s AND is_public = TRUE
            ''',
            (variant_id,)
        )

        variant = cur.fetchone()

        if variant is None:
            flash('Вариант не найден')
            return redirect('/tests')

        cur.execute(
            '''
            SELECT
                tasks.*,
                variant_tasks.id AS variant_task_id
            FROM variant_tasks
            JOIN tasks
                ON tasks.id = variant_tasks.task_id
            WHERE variant_tasks.var_id = %s
            ORDER BY variant_tasks.id
            ''',
            (variant_id,)
        )

        var_tasks = cur.fetchall()

        return render_template(
            'var.html',
            variant=variant,
            var_tasks=var_tasks,
            variant_id=variant_id,
            is_saved_variant=True
        )
    finally:
        cur.close()
        conn.close()


# =========================================================
# АДМИН: УДАЛИТЬ ВАРИАНТ
# =========================================================

@tasks_bp.route('/delete_variant/<int:variant_id>', methods=['POST'])
@admin_only
def delete_variant(variant_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            SELECT id
            FROM variants
            WHERE id = %s
            ''',
            (variant_id,)
        )

        variant = cur.fetchone()

        if variant is None:
            flash('Вариант не найден')
            return redirect('/tests')

        cur.execute(
            '''
            DELETE FROM variant_tasks
            WHERE var_id = %s
            ''',
            (variant_id,)
        )

        cur.execute(
            '''
            DELETE FROM variants
            WHERE id = %s
            ''',
            (variant_id,)
        )

        conn.commit()

        flash('Вариант успешно удалён!')
        return redirect('/tests')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================================================
# ПРОВЕРКА ГОТОВОГО ВАРИАНТА
# =========================================================

@tasks_bp.route('/check_saved_variant/<int:variant_id>', methods=['POST'])
@regs_only
def check_saved_variant(variant_id):
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            SELECT *
            FROM variants
            WHERE id = %s AND is_public = TRUE
            ''',
            (variant_id,)
        )
        variant = cur.fetchone()

        if variant is None:
            return jsonify({
                'success': False,
                'error': 'Вариант не найден'
            }), 404

        cur.execute(
            '''
            SELECT tasks.*
            FROM variant_tasks
            JOIN tasks ON tasks.id = variant_tasks.task_id
            WHERE variant_tasks.var_id = %s
            ORDER BY variant_tasks.id
            ''',
            (variant_id,)
        )
        var_tasks = cur.fetchall()

        score = 0
        results = []

        for task in var_tasks:
            task_id = task['id']
            user_answer = request.form.get(f'answer_{task_id}', '').strip()
            correct_answer = (task['answer'] or '').strip()
            is_correct = int(user_answer == correct_answer)

            if is_correct == 1:
                score += 1

            results.append({
                'task_id': task_id,
                'task_number': task['number'],
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'correct': is_correct
            })

            cur.execute(
                '''
                SELECT COUNT(*) AS total
                FROM task_attempts
                WHERE user_id = %s AND task_id = %s
                ''',
                (user_id, task_id)
            )
            attempt_number = cur.fetchone()['total'] + 1

            cur.execute(
                '''
                INSERT INTO task_attempts(user_id, task_id, correct, attempt_number)
                VALUES(%s, %s, %s, %s)
                ''',
                (user_id, task_id, is_correct, attempt_number)
            )

            status = 'Правильно!' if is_correct == 1 else 'Неправильно!'
            cur.execute(
                '''
                INSERT INTO user_tasks(user_id, task_id, status, completed_at)
                VALUES(%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, task_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    completed_at = CURRENT_TIMESTAMP
                ''',
                (user_id, task_id, status)
            )

        # Создаём запись в истории пользователя
        cur.execute(
            '''
            INSERT INTO variants(user_id, score, created_at, name, year, is_public)
            VALUES(%s, %s, %s, %s, %s, FALSE)
            RETURNING id
            ''',
            (user_id, score, datetime.now(), variant['name'], variant['year'])
        )
        result_variant_id = cur.fetchone()['id']

        for res in results:
            cur.execute(
                '''
                INSERT INTO variant_tasks(
                    var_id, task_id, task_number, user_id, user_answer, correct_answer, correct
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    result_variant_id,
                    res['task_id'],
                    res['task_number'],
                    user_id,
                    res['user_answer'],
                    res['correct_answer'],
                    res['correct']
                )
            )

        conn.commit()

        return jsonify({
            'success': True,
            'variant_id': variant_id,
            'score': score,
            'total': len(var_tasks),
            'results': results
        })

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================================================
# СГЕНЕРИРОВАТЬ СЛУЧАЙНЫЙ ВАРИАНТ
# =========================================================

@tasks_bp.route('/generate_var')
@regs_only
def generate_var():
    conn = get_db()
    cur = conn.cursor()

    try:
        var_tasks = []
        nums = list(range(1, 20))

        for number in nums:
            cur.execute(
                '''
                SELECT *
                FROM tasks
                WHERE number = %s
                ''',
                (number,)
            )
            t_list = cur.fetchall()

            if t_list:
                var_tasks.append(random.choice(t_list))

        return render_template(
            'var.html',
            variant=None,
            var_tasks=var_tasks,
            is_saved_variant=False
        )
    finally:
        cur.close()
        conn.close()


# =========================================================
# ПРОВЕРКА СГЕНЕРИРОВАННОГО ВАРИАНТА
# =========================================================

@tasks_bp.route('/check_var', methods=['POST'])
@regs_only
def check_var():
    conn = get_db()
    cur = conn.cursor()

    try:
        task_ids = request.form.getlist('task_id')
        score = 0
        answers = []

        for task_id in task_ids:
            cur.execute(
                '''
                SELECT *
                FROM tasks
                WHERE id = %s
                ''',
                (task_id,)
            )
            task = cur.fetchone()

            if task is None:
                continue

            user_answer = request.form.get(f'answer_{task_id}', '').strip()
            correct = (task['answer'] or '').strip()
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

        cur.execute(
            '''
            INSERT INTO variants(user_id, score, created_at, name, year, is_public)
            VALUES(%s, %s, %s, %s, %s, FALSE)
            RETURNING id
            ''',
            (
                session['user_id'],
                score,
                datetime.now(),
                'Сгенерированный вариант',
                datetime.now().year
            )
        )

        var_id = cur.fetchone()['id']

        for ans in answers:
            cur.execute(
                '''
                INSERT INTO variant_tasks(
                    var_id, task_id, task_number, user_id, user_answer, correct_answer, correct
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    var_id,
                    ans['task_id'],
                    ans['task_number'],
                    session['user_id'],
                    ans['user_answer'],
                    ans['correct_answer'],
                    ans['correct']
                )
            )

        conn.commit()

        return {
            'score': score,
            'total': len(task_ids)
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================================================
# СТАТИСТИКА
# =========================================================

@tasks_bp.route('/statistics')
@regs_only
def statistics():
    user_id = session['user_id']

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

        solved_count = all_count(user_id)
        correct = correct_count(user_id)
        goal = user['goal'] if user and 'goal' in user else 0

        percent = int(correct / solved_count * 100) if solved_count else 0

        # Стрик дней
        cur.execute(
            '''
            SELECT DISTINCT active_date FROM (
                SELECT DATE(completed_at) AS active_date
                FROM user_tasks 
                WHERE user_id = %s AND completed_at IS NOT NULL
                
                UNION
                
                SELECT DATE(created_at) AS active_date
                FROM variants 
                WHERE user_id = %s AND created_at IS NOT NULL
            ) AS dates
            ORDER BY active_date DESC
            ''',
            (user_id, user_id)
        )

        date_rows = cur.fetchall()
        active_dates = [row['active_date'] for row in date_rows]

        streak = 0
        today = date.today()

        if active_dates:
            parsed_dates = []
            for d in active_dates:
                if isinstance(d, str):
                    parsed_dates.append(datetime.strptime(d, '%Y-%m-%d').date())
                elif isinstance(d, datetime):
                    parsed_dates.append(d.date())
                else:
                    parsed_dates.append(d)

            if parsed_dates[0] == today:
                streak = 1
                check_date = today - timedelta(days=1)
                dates_to_check = parsed_dates[1:]
            elif parsed_dates[0] == today - timedelta(days=1):
                streak = 1
                check_date = today - timedelta(days=2)
                dates_to_check = parsed_dates[1:]
            else:
                dates_to_check = []

            for d in dates_to_check:
                if d == check_date:
                    streak += 1
                    check_date -= timedelta(days=1)
                elif d > check_date:
                    continue
                else:
                    break

        # Активность по дням
        cur.execute(
            '''
            SELECT DATE(completed_at) AS task_date, COUNT(*) AS count
            FROM user_tasks
            WHERE user_id = %s AND completed_at IS NOT NULL
            GROUP BY DATE(completed_at)
            ''',
            (user_id,)
        )
        activity_rows = cur.fetchall()
        activity_data = {}
        for r in activity_rows:
            d_str = r['task_date'].strftime('%Y-%m-%d') if isinstance(r['task_date'], (date, datetime)) else str(r['task_date'])
            activity_data[d_str] = r['count']

        # Процент решения по номерам
        cur.execute(
            '''
            SELECT
                tasks.number,
                ROUND(
                    100.0 * SUM(
                        CASE WHEN user_tasks.status LIKE 'Правильно%%' THEN 1 ELSE 0 END
                    ) / COUNT(*),
                    1
                ) AS percent
            FROM user_tasks
            JOIN tasks ON user_tasks.task_id = tasks.id
            WHERE user_tasks.user_id = %s
            GROUP BY tasks.number
            ORDER BY tasks.number
            ''',
            (user_id,)
        )

        data = cur.fetchall()
        numbers = [row['number'] for row in data]
        percents = [row['percent'] for row in data]

        # Первые попытки
        cur.execute(
            '''
            SELECT
                tasks.number,
                COUNT(CASE WHEN task_attempts.attempt_number = 1 THEN 1 END) AS total_first_attempts,
                SUM(
                    CASE
                        WHEN task_attempts.attempt_number = 1 AND task_attempts.correct = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS correct_first_attempts
            FROM task_attempts
            JOIN tasks ON tasks.id = task_attempts.task_id
            WHERE task_attempts.user_id = %s
            GROUP BY tasks.number
            ORDER BY tasks.number
            ''',
            (user_id,)
        )

        raw = cur.fetchall()
        first_attempts_numbers = []
        first_attempts_percents = []

        for r in raw:
            num = r['number']
            total = r['total_first_attempts'] or 0
            first = r['correct_first_attempts'] or 0
            p_first = (first / total * 100) if total > 0 else 0

            first_attempts_numbers.append(num)
            first_attempts_percents.append(round(p_first, 2))

        # История прохождений
        cur.execute(
            '''
            SELECT
                variant_tasks.var_id,
                tasks.number AS task_number,
                variant_tasks.task_id,
                variant_tasks.user_answer,
                variant_tasks.correct_answer,
                variant_tasks.correct,
                variants.score,
                variants.created_at,
                variants.name,
                variants.year
            FROM variant_tasks
            JOIN variants ON variant_tasks.var_id = variants.id
            JOIN tasks ON variant_tasks.task_id = tasks.id
            WHERE variants.user_id = %s
            ORDER BY variants.created_at DESC, variant_tasks.var_id DESC, tasks.number
            ''',
            (user_id,)
        )

        history_rows = cur.fetchall()
        history = {}

        for row in history_rows:
            var_id = row['var_id']
            if var_id not in history:
                history[var_id] = {
                    'name': row['name'],
                    'year': row['year'],
                    'score': row['score'],
                    'created_at': row['created_at'],
                    'tasks': []
                }
            history[var_id]['tasks'].append(row)
        CONVERT_TABLE = {
            0: 0, 1: 6, 2: 11, 3: 17, 4: 22, 5: 27, 6: 34, 7: 40, 8: 46,
            9: 52, 10: 58, 11: 64, 12: 70, 13: 72, 14: 74, 15: 76, 16: 78,
            17: 80, 18: 82, 19: 84, 20: 86, 21: 88, 22: 90, 23: 92, 24: 94,
            25: 96, 26: 98, 27: 100, 28: 100, 29: 100, 30: 100, 31: 100, 32: 100
        }

# Пример простой логики: переводим среднюю точность в примерный первичный балл из 32
        estimated_primary = round((percent / 100) * 32)
        predicted_score = CONVERT_TABLE.get(estimated_primary, 0)

        return render_template(
            'statistics.html',
            user=user,
            solved_count=solved_count,
            correct=correct,
            goal=goal,
            percent=percent,
            streak=streak,
            activity_data=activity_data,
            numbers=numbers,
            percents=percents,
            first_attempts_numbers=first_attempts_numbers,
            first_attempts_percents=first_attempts_percents,
            variant_table=history,
            history=history,
            predicted_score=predicted_score
        )
    finally:
        cur.close()
        conn.close()