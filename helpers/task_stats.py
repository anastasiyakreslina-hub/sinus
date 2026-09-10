# =========================================================
# ОБЩАЯ ЛОГИКА ДЛЯ ЗАДАЧ (используется в tasks.py и variants.py)
# =========================================================

from datetime import date, datetime, timedelta


def get_first_attempt_stats(cur):
    """Процент правильных решений с первой попытки по каждой задаче."""
    cur.execute('''
        SELECT
            task_id,
            COUNT(*) AS total,
            SUM(CASE WHEN attempt_number = 1 AND correct = 1 THEN 1 ELSE 0 END) AS correct_first_attempts
        FROM task_attempts
        GROUP BY task_id
    ''')

    stats = {}
    for r in cur.fetchall():
        total = r['total'] or 0
        first = r['correct_first_attempts'] or 0
        stats[r['task_id']] = round((first / total * 100) if total else 0, 2)

    return stats


def record_attempt(cur, user_id, task_id, is_correct):
    """Записывает попытку решения и обновляет статус задачи у пользователя. Возвращает номер попытки."""
    cur.execute(
        'SELECT COUNT(*) AS total FROM task_attempts WHERE user_id = %s AND task_id = %s',
        (user_id, task_id)
    )
    attempt_number = cur.fetchone()['total'] + 1

    cur.execute(
        'INSERT INTO task_attempts(user_id, task_id, correct, attempt_number) VALUES(%s, %s, %s, %s)',
        (user_id, task_id, is_correct, attempt_number)
    )

    status = 'Правильно!' if is_correct else 'Неправильно!'
    cur.execute('''
        INSERT INTO user_tasks(user_id, task_id, status, completed_at)
        VALUES(%s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, task_id)
        DO UPDATE SET status = EXCLUDED.status, completed_at = CURRENT_TIMESTAMP
    ''', (user_id, task_id, status))

    return attempt_number


def calculate_streak(active_dates):
    """Считает текущий стрик дней подряд. active_dates — список date/datetime/str по убыванию."""
    if not active_dates:
        return 0

    parsed = []
    for d in active_dates:
        if isinstance(d, str):
            parsed.append(datetime.strptime(d, '%Y-%m-%d').date())
        elif isinstance(d, datetime):
            parsed.append(d.date())
        else:
            parsed.append(d)

    today = date.today()

    if parsed[0] == today:
        streak = 1
        check_date = today - timedelta(days=1)
        rest = parsed[1:]
    elif parsed[0] == today - timedelta(days=1):
        streak = 1
        check_date = today - timedelta(days=2)
        rest = parsed[1:]
    else:
        return 0

    for d in rest:
        if d == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif d > check_date:
            continue
        else:
            break

    return streak