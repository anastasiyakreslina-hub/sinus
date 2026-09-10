# =========================================================
# СТАТИСТИКА
# =========================================================

from datetime import date, datetime

from flask import Blueprint, render_template, session

from database import get_db
from decorators import regs_only
from utils import all_count, correct_count
from helpers.task_stats import calculate_streak


statistics_bp = Blueprint('statistics', __name__)

# Перевод первичного балла (из 32) в тестовый (из 100), по шкале ЕГЭ.
CONVERT_TABLE = {
    0: 0, 1: 6, 2: 11, 3: 17, 4: 22, 5: 27, 6: 34, 7: 40, 8: 46,
    9: 52, 10: 58, 11: 64, 12: 70, 13: 72, 14: 74, 15: 76, 16: 78,
    17: 80, 18: 82, 19: 84, 20: 86, 21: 88, 22: 90, 23: 92, 24: 94,
    25: 96, 26: 98, 27: 100, 28: 100, 29: 100, 30: 100, 31: 100, 32: 100
}


@statistics_bp.route('/statistics')
@regs_only
def statistics():
    user_id = session['user_id']

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()

        solved_count = all_count(user_id)
        correct = correct_count(user_id)
        goal = user['goal'] if user and 'goal' in user else 0
        percent = int(correct / solved_count * 100) if solved_count else 0

        # Стрик дней
        cur.execute('''
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
        ''', (user_id, user_id))

        active_dates = [row['active_date'] for row in cur.fetchall()]
        streak = calculate_streak(active_dates)

        # Активность по дням
        cur.execute('''
            SELECT DATE(completed_at) AS task_date, COUNT(*) AS count
            FROM user_tasks
            WHERE user_id = %s AND completed_at IS NOT NULL
            GROUP BY DATE(completed_at)
        ''', (user_id,))

        activity_data = {}
        for r in cur.fetchall():
            d = r['task_date']
            d_str = d.strftime('%Y-%m-%d') if isinstance(d, (date, datetime)) else str(d)
            activity_data[d_str] = r['count']

        # Процент решения по номерам
        cur.execute('''
            SELECT
                tasks.number,
                ROUND(100.0 * SUM(CASE WHEN user_tasks.status LIKE 'Правильно%%' THEN 1 ELSE 0 END) / COUNT(*), 1) AS percent
            FROM user_tasks
            JOIN tasks ON user_tasks.task_id = tasks.id
            WHERE user_tasks.user_id = %s
            GROUP BY tasks.number
            ORDER BY tasks.number
        ''', (user_id,))

        data = cur.fetchall()
        numbers = [row['number'] for row in data]
        percents = [row['percent'] for row in data]

        # Первые попытки
        cur.execute('''
            SELECT
                tasks.number,
                COUNT(CASE WHEN task_attempts.attempt_number = 1 THEN 1 END) AS total_first_attempts,
                SUM(CASE WHEN task_attempts.attempt_number = 1 AND task_attempts.correct = 1 THEN 1 ELSE 0 END) AS correct_first_attempts
            FROM task_attempts
            JOIN tasks ON tasks.id = task_attempts.task_id
            WHERE task_attempts.user_id = %s
            GROUP BY tasks.number
            ORDER BY tasks.number
        ''', (user_id,))

        first_attempts_numbers = []
        first_attempts_percents = []

        for r in cur.fetchall():
            total = r['total_first_attempts'] or 0
            first = r['correct_first_attempts'] or 0
            p_first = (first / total * 100) if total > 0 else 0

            first_attempts_numbers.append(r['number'])
            first_attempts_percents.append(round(p_first, 2))

        # История прохождений
        cur.execute('''
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
        ''', (user_id,))

        history = {}
        for row in cur.fetchall():
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

        scores = [variant['score'] for variant in history.values()]
        avg_variant_score = round(sum(scores) / len(scores), 1) if scores else 0

        # Переводим среднюю точность в примерный первичный балл из 32, затем в тестовый
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
            predicted_score=predicted_score,
            avg_variant_score=avg_variant_score
        )
    finally:
        cur.close()
        conn.close()