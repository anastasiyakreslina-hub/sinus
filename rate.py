from datetime import datetime
from functools import wraps
from flask import flash, redirect, url_for

# ============================================================
# НАСТРОЙКИ ТАРИФОВ
# ============================================================
SIMPLE_TARIFF = "simple"
PRO_TARIFF = "pro"

# Цена Pro в копейках (29900 = 299 рублей)
PRO_PRICE = 29900

# Срок действия Pro (в днях)
PRO_DAYS = 30


# ============================================================
# АДМИНИСТРАТОР
# ============================================================
def is_admin(user: dict) -> bool:
    """Проверяет, является ли пользователь администратором.

    Администратор всегда получает Pro, независимо от tariff и pro_until.
    """
    if not user:
        return False

    return user.get("role") == "admin"


# ============================================================
# ПРОВЕРКА PRO
# ============================================================
def has_pro_access(user: dict) -> bool:
    """Проверяет, есть ли у пользователя активный Pro.

    Правила:
    1. Администратор -> всегда Pro.
    2. Обычный пользователь -> Pro, если:
       - tariff == "pro"
       - pro_until существует
       - pro_until ещё не наступил.
    """
    if not user:
        return False

    # Администратор всегда имеет Pro
    if is_admin(user):
        return True

    # Проверяем тариф
    if user.get("tariff") != PRO_TARIFF:
        return False

    # Получаем дату окончания
    pro_until = user.get("pro_until")

    if not pro_until:
        return False

    # PostgreSQL обычно возвращает datetime,
    # но на всякий случай поддерживаем строку.
    if isinstance(pro_until, str):
        try:
            pro_until = datetime.fromisoformat(pro_until)
        except ValueError:
            return False

    # Учитываем timezone-aware / timezone-naive datetime
    if pro_until.tzinfo:
        now = datetime.now(pro_until.tzinfo)
    else:
        now = datetime.now()

    return pro_until > now


# ============================================================
# НАЗВАНИЕ ТАРИФА
# ============================================================
def get_tariff_name(user: dict) -> str:
    """Возвращает название активного тарифа.

    admin / активный Pro -> "pro"
    остальные -> "simple"
    """
    if has_pro_access(user):
        return PRO_TARIFF

    return SIMPLE_TARIFF


# ============================================================
# ИНФОРМАЦИЯ О ТАРИФЕ
# ============================================================
def get_tariff_info(user: dict) -> dict:
    """Возвращает всю необходимую информацию о тарифе.

    Используется в app.py и HTML-шаблонах.
    """
    if not user:
        return {
            "name": SIMPLE_TARIFF,
            "is_pro": False,
            "is_admin": False,
            "pro_until": None,
        }

    admin = is_admin(user)
    pro = has_pro_access(user)

    return {
        "name": PRO_TARIFF if pro else SIMPLE_TARIFF,
        "is_pro": pro,
        "is_admin": admin,
        # Для админа возвращаем "Бессрочно", либо его реальную дату, если она есть
        "pro_until": user.get("pro_until") or ("Бессрочно" if admin else None),
    }

# ============================================================
# ИНФОРМАЦИЯ О PRO
# ============================================================
def get_pro_offer() -> dict:
    """Возвращает информацию для страницы/модалки покупки Pro."""
    return {
        "name": "Pro",
        "price": PRO_PRICE,
        "price_rubles": PRO_PRICE // 100,
        "days": PRO_DAYS,
        "features": [
            "Полный банк задач",
            "Все варианты ЕГЭ и ОГЭ",
            "Умная работа над ошибками",
            "Расширенная статистика",
            "Доступ ко всем теоретическим материалам",
        ],
    }


# ============================================================
# ПРОВЕРКА PRO ВО ВРЕМЯ ЗАПРОСА
# ============================================================
def require_pro(user: dict):
    """Проверяет наличие Pro.

    Если Pro есть: возвращает None
    Если Pro нет: перенаправляет пользователя на главную.
    """
    if has_pro_access(user):
        return None

    flash("Эта возможность доступна только на тарифе Pro.", "tariff")
    return redirect(url_for("main.home"))


# ============================================================
# ПРОВЕРКА АВТОРИЗАЦИИ + PRO
# ============================================================
def require_pro_login(user: dict):
    """Проверяет:
    1. Авторизован ли пользователь.
    2. Есть ли у него Pro.
    """
    if not user:
        return redirect(url_for("auth.login"))

    return require_pro(user)


# ============================================================
# ДЕКОРАТОР ДЛЯ PRO-СТРАНИЦ
# ============================================================
def pro_required(get_user_func):
    """Декоратор для защиты Flask-роутов.

    Пример:
        @app.route("/statistics")
        @pro_required(get_current_user)
        def statistics():
            return render_template("statistics.html")
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_user_func()
            redirect_response = require_pro_login(user)

            if redirect_response:
                return redirect_response

            return f(*args, **kwargs)

        return decorated_function

    return decorator