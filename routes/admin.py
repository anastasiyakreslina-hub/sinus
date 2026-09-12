from functools import wraps
from flask import Blueprint, render_template, session, redirect
from database import get_db
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Декоратор проверки прав админа через сессию
def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route('/dashboard')
@admin_only
def dashboard():
    conn = get_db()
    cur = conn.cursor()

    try:
        # 1. Метрики по пользователям и подпискам
        cur.execute("SELECT COUNT(*) AS count FROM users;")
        total_users = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) AS count FROM users WHERE tariff = 'pro' AND pro_until > NOW();")
        active_subscriptions = cur.fetchone()['count']

        # Подсчет новых пользователей за сегодня с учетом формата DD.MM.YYYY
        cur.execute("""
            SELECT COUNT(*) AS count 
            FROM users 
            WHERE reg_date IS NOT NULL 
              AND reg_date != '' 
              AND TO_DATE(reg_date, 'DD.MM.YYYY') = CURRENT_DATE;
        """)
        new_users_today = cur.fetchone()['count']

        # Активные за последние 30 дней (кто решал задачи)
        cur.execute("""
            SELECT COUNT(DISTINCT user_id) AS count 
            FROM user_tasks 
            WHERE completed_at >= NOW() - INTERVAL '30 days';
        """)
        active_users = cur.fetchone()['count']

        # 2. Метрики контента и активности
        cur.execute("SELECT COUNT(*) AS count FROM tasks;")
        total_tasks = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) AS count FROM variants;")
        total_variants = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) AS count FROM user_tasks;")
        total_solutions = cur.fetchone()['count']

        # 3. Таблица последних зарегистрированных пользователей
        cur.execute("""
            SELECT 
                u.id, 
                u.username, 
                u.reg_date AS created_at,
                u.tariff,
                u.pro_until,
                COALESCE(ut.solved_count, 0) AS solved_count
            FROM users u
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS solved_count 
                FROM user_tasks 
                GROUP BY user_id
            ) ut ON u.id = ut.user_id
            ORDER BY u.id DESC 
            LIMIT 10;
        """)
        recent_users_raw = cur.fetchall()

        recent_users = []
        for u in recent_users_raw:
            has_sub = u['tariff'] == 'pro' and u['pro_until'] and u['pro_until'] > datetime.now()
            recent_users.append({
                'id': u['id'],
                'username': u['username'] or f"User #{u['id']}",
                'email': '—',
                'created_at': u['created_at'] or '—',
                'solved_count': u['solved_count'],
                'has_subscription': has_sub
            })

        # 4. Данные для графика регистраций (за последние 14 дней)
        cur.execute("""
            SELECT TO_CHAR(TO_DATE(reg_date, 'DD.MM.YYYY'), 'DD.MM') AS date, COUNT(*) AS count
            FROM users
            WHERE reg_date IS NOT NULL 
              AND reg_date != ''
              AND TO_DATE(reg_date, 'DD.MM.YYYY') >= CURRENT_DATE - INTERVAL '14 days'
            GROUP BY TO_DATE(reg_date, 'DD.MM.YYYY')
            ORDER BY TO_DATE(reg_date, 'DD.MM.YYYY') ASC;
        """)
        reg_data = cur.fetchall()
        reg_dates = [r['date'] for r in reg_data]
        reg_counts = [r['count'] for r in reg_data]

        # 5. Данные для графика решенных задач (за последние 14 дней)
        cur.execute("""
            SELECT TO_CHAR(completed_at::date, 'DD.MM') AS date, COUNT(*) AS count
            FROM user_tasks
            WHERE completed_at >= CURRENT_DATE - INTERVAL '14 days'
            GROUP BY completed_at::date
            ORDER BY completed_at::date ASC;
        """)
        sol_data = cur.fetchall()
        solutions_dates = [s['date'] for s in sol_data]
        solutions_counts = [s['count'] for s in sol_data]

    finally:
        cur.close()
        conn.close()

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        active_users=active_users,
        active_subscriptions=active_subscriptions,
        new_users_today=new_users_today,
        total_tasks=total_tasks,
        total_variants=total_variants,
        total_solutions=total_solutions,
        recent_users=recent_users,
        reg_dates=reg_dates,
        reg_counts=reg_counts,
        solutions_dates=solutions_dates,
        solutions_counts=solutions_counts
    )