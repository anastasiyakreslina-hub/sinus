# Главная, "О нас", политика конфиденциальности

from flask import Blueprint, render_template, redirect, session
from database import get_db
from decorators import regs_only
from utils import all_count, correct_count
from datetime import date

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@regs_only
def home():
    if 'user' in session:
        conn = get_db()
        cur = conn.cursor()
        # Заменен ? на %s для PostgreSQL
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user is None:
            session.clear()
            return redirect('/login')
            
        goal = user['goal']
        solved_cnt = all_count(session['user_id'])
        correct_cnt = correct_count(session['user_id'])
        percent = int((correct_cnt / solved_cnt) * 100) if solved_cnt else 0
        return render_template('index.html', goal=goal, user=user, 
                               solved_count=solved_cnt, correct=correct_cnt, percent=percent)
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