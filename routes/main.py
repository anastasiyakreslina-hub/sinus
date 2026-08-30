# Главная, "О нас", политика конфиденциальности

from flask import Blueprint, render_template, redirect, session
from database import get_db
from decorators import regs_only
from utils import all_count, correct_count
from datetime import date, datetime, timedelta

main_bp = Blueprint('main', __name__)

def calculate_user_streak(user_id, conn):
    """
    Вычисляет количество дней непрерывного решения задач с учетом часового пояса МСК (+3 часа).
    """
    cur = conn.cursor()
    
    # Приводимcompleted_at к МСК времени (AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')
    # Еслиcompleted_at сохранен как timestamp without time zone в UTC:
    cur.execute('''
        SELECT DISTINCT DATE(completed_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow') as task_date 
        FROM user_tasks 
        WHERE user_id = %s 
        ORDER BY task_date DESC
    ''', (user_id,))
    
    rows = cur.fetchall()
    cur.close()

    if not rows:
        return 0

    dates = [row['task_date'] if isinstance(row, dict) else row[0] for row in rows]
    
    # Считаем "сегодня" также по московскому времени
    # Для вычисления даты по МСК:
    today = (datetime.utcnow() + timedelta(hours=3)).date()
    yesterday = today - timedelta(days=1)

    # Если последняя активность была раньше чем вчера — стрик сбросился
    if dates[0] < yesterday:
        return 0

    streak = 1
    current_expected = dates[0] - timedelta(days=1)

    for d in dates[1:]:
        if d == current_expected:
            streak += 1
            current_expected -= timedelta(days=1)
        elif d > current_expected:
            continue
        else:
            break

    return streak


@main_bp.route('/')
@regs_only
def home():
    if 'user' in session:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()

        if user is None:
            cur.close()
            conn.close()
            session.clear()
            return redirect('/login')

        # Рассчитываем стрик и данные пользователя
        streak = calculate_user_streak(session['user_id'], conn)
        
        # Данные по тарифу Pro (если есть поле is_pro / pro_until в БД)
        tariff_info = {
            'is_pro': user.get('is_pro', False) if isinstance(user, dict) else getattr(user, 'is_pro', False),
            'is_admin': user.get('is_admin', False) if isinstance(user, dict) else getattr(user, 'is_admin', False),
            'pro_until': user.get('pro_until', None) if isinstance(user, dict) else getattr(user, 'pro_until', None)
        }

        cur.close()
        conn.close()

        username = user['username'] if isinstance(user, dict) else user[1]
        goal = user['goal'] if isinstance(user, dict) else user['goal']
        solved_cnt = all_count(session['user_id'])
        correct_cnt = correct_count(session['user_id'])
        percent = int((correct_cnt / solved_cnt) * 100) if solved_cnt else 0

        return render_template(
            'index.html',
            username=username,
            goal=goal,
            user=user,
            solved_count=solved_cnt,
            correct=correct_cnt,
            percent=percent,
            streak=streak,
            tariff_info=tariff_info
        )

    return redirect('/login')


@main_bp.route('/about')
@regs_only
def about():
    def read_static_file(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""

    return render_template(
        'about.html',
        about_text=read_static_file('static/texts/about.txt'),
        functions_text=read_static_file('static/texts/functions.txt'),
        forWho_text=read_static_file('static/texts/forWho.txt'),
        include_text=read_static_file('static/texts/include.txt')
    )


@main_bp.route("/offer")
def offer():
    return render_template(
        "offer.html",
        offer_date=date.today().strftime("%d.%m.%Y"),
        seller_name="Креслина Анастасия Владимировна",
        seller_status="самозанятая",
        seller_inn="701775365157",
        seller_email="anastasiyakreslina@gmail.com",
        pro_price=299,
        pro_days=30
    )


@main_bp.route("/privacypolicy")
def privacypolicy():
    return render_template(
        "privacypolicy.html",
        privacypolicy_date=date.today().strftime("%d.%m.%Y"),
        seller_name="Креслина Анастасия Владимировна",
        seller_status="самозанятая",
        seller_inn="701775365157",
        seller_email="anastasiyakreslina@gmail.com"
    )


@main_bp.route("/refund")
def refund():
    return render_template(
        "refund.html",
        refund_date=date.today().strftime("%d.%m.%Y"),
        seller_name="Креслина Анастасия Владимировна",
        seller_status="самозанятая",
        seller_inn="701775365157",
        seller_email="anastasiyakreslina@gmail.com"
    )


@main_bp.route('/error')
@regs_only
def error():
    return render_template('error.html')