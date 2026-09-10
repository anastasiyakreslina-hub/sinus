# routes/payment.py

import os
import uuid
import ipaddress
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, session, flash, request, jsonify

from database import get_db
from rate import PRO_DAYS, PRO_PRICE, has_pro_access, get_pro_offer


# ============================================================
# BLUEPRINT
# ============================================================

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")


# ============================================================
# ЮKASSA
# ============================================================
# Устанавливаются через переменные окружения:
#   export YOOKASSA_SHOP_ID="..."
#   export YOOKASSA_SECRET_KEY="..."

YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")

# Официальные подсети ЮKassa, с которых приходят вебхуки.
# https://yookassa.ru/developers/using-api/webhooks#ip
YOOKASSA_IP_RANGES = [
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "77.75.154.128/25",
    "2a02:5180::/32",
]


def _configure_yookassa():
    from yookassa import Configuration
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY


def _get_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


def _grant_pro(user, user_id):
    now = datetime.now()
    old_until = user.get("pro_until")
    start_date = old_until if (old_until and old_until > now) else now
    pro_until = start_date + timedelta(days=PRO_DAYS)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET tariff = 'pro', pro_until = %s WHERE id = %s",
        (pro_until, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()
    return pro_until


def _is_yookassa_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in ipaddress.ip_network(net) for net in YOOKASSA_IP_RANGES)


def _client_ip() -> str:
    # Если сервис стоит за доверенным прокси (nginx и т.п.), убедитесь,
    # что X-Forwarded-For выставляется именно прокси, а не клиентом.
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr


# ============================================================
# СТРАНИЦА ОПЛАТЫ
# ============================================================

@payment_bp.route("/")
def payment_page():
    """Страница оплаты Pro."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    offer = get_pro_offer()
    return render_template("payment.html", offer=offer)


# ============================================================
# СОЗДАНИЕ ПЛАТЕЖА
# ============================================================

@payment_bp.route("/create", methods=["POST"])
def create_payment():
    """Создаёт платёж в ЮKassa."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = _get_user(user_id)
    if not user:
        flash("Пользователь не найден.", "error")
        return redirect(url_for("main.home"))

    if user.get("role") == "admin":
        flash("У администратора уже есть Pro.", "info")
        return redirect(url_for("main.home"))

    if has_pro_access(user):
        flash("У вас уже активен тариф Pro.", "info")
        return redirect(url_for("main.home"))

    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        flash("Оплата пока не настроена. Добавьте данные ЮKassa.", "error")
        return redirect(url_for("payment.payment_page"))

    try:
        from yookassa import Payment
        _configure_yookassa()

        idempotence_key = str(uuid.uuid4())

        payment = Payment.create(
            {
                "amount": {"value": f"{PRO_PRICE / 100:.2f}", "currency": "RUB"},
                "capture": True,
                "confirmation": {
                    "type": "redirect",
                    "return_url": url_for("payment.payment_success", _external=True),
                },
                "description": f"Sinus Pro — {PRO_DAYS} дней",
                "metadata": {"user_id": str(user_id), "tariff": "pro"},
            },
            idempotence_key,
        )

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET last_payment_id = %s WHERE id = %s",
            (payment.id, user_id),
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect(payment.confirmation.confirmation_url)

    except Exception as e:
        print("Ошибка создания платежа:", e)
        flash("Не удалось создать платёж. Попробуйте ещё раз.", "error")
        return redirect(url_for("payment.payment_page"))


# ============================================================
# ВОЗВРАТ ПОСЛЕ ОПЛАТЫ (для UX — не источник истины)
# ============================================================

@payment_bp.route("/success")
def payment_success():
    """
    Пользователь возвращается сюда после оплаты.

    ВАЖНО: сам факт перехода на эту страницу НЕ означает, что платёж
    завершён. Мы проверяем статус через API, но окончательным и
    надёжным источником истины должен быть вебхук ниже — переход
    сюда может не произойти вовсе (пользователь закрыл вкладку).
    """
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = _get_user(user_id)
    if not user:
        return redirect(url_for("auth.login"))

    payment_id = user.get("last_payment_id")
    if not payment_id:
        flash("Платёж не найден.", "error")
        return redirect(url_for("main.home"))

    try:
        from yookassa import Payment
        _configure_yookassa()

        payment = Payment.find_one(payment_id)

        if payment.status == "succeeded":
            paid_amount = float(payment.amount.value)
            required_amount = PRO_PRICE / 100

            if paid_amount < required_amount:
                flash("Сумма платежа не соответствует тарифу.", "error")
                return redirect(url_for("main.home"))

            if not has_pro_access(user):
                _grant_pro(user, user_id)

            flash("Оплата прошла успешно! Pro активирован.", "success")

        elif payment.status == "pending":
            flash("Платёж ещё обрабатывается. Попробуйте обновить страницу немного позже.", "info")

        else:
            flash("Платёж не был завершён.", "error")

    except Exception as e:
        print("Ошибка проверки платежа:", e)
        flash("Не удалось проверить статус платежа.", "error")

    return redirect(url_for("main.home"))


# ============================================================
# ВЕБХУК ЮKASSA (источник истины)
# ============================================================
# Настройте этот URL в личном кабинете ЮKassa:
#   https://<ваш-домен>/payment/webhook
# События: payment.succeeded, payment.canceled

@payment_bp.route("/webhook", methods=["POST"])
def payment_webhook():
    # 1. Проверяем, что запрос действительно от ЮKassa.
    if not _is_yookassa_ip(_client_ip()):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "bad request"}), 400

    event = data.get("event")
    payment_obj = data.get("object", {})
    payment_id = payment_obj.get("id")

    if not payment_id:
        return jsonify({"error": "bad request"}), 400

    if event != "payment.succeeded":
        # Другие события (canceled и т.п.) — просто подтверждаем приём.
        return jsonify({"status": "ok"}), 200

    # 2. НИКОГДА не доверяем статусу из тела запроса — запрашиваем
    #    платёж напрямую через API, чтобы исключить подделку вебхука.
    try:
        from yookassa import Payment
        _configure_yookassa()
        payment = Payment.find_one(payment_id)
    except Exception as e:
        print("Ошибка получения платежа по вебхуку:", e)
        return jsonify({"error": "internal error"}), 500

    if payment.status != "succeeded":
        return jsonify({"status": "ignored"}), 200

    metadata = payment.metadata or {}
    user_id = metadata.get("user_id")

    if not user_id:
        return jsonify({"error": "no user_id"}), 400

    user = _get_user(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    paid_amount = float(payment.amount.value)
    required_amount = PRO_PRICE / 100

    if paid_amount < required_amount:
        print(f"Webhook: недостаточная сумма для платежа {payment_id}")
        return jsonify({"status": "ignored"}), 200

    # 3. Идемпотентность: не продлеваем Pro повторно для одного платежа.
    if user.get("last_paid_payment_id") == payment_id:
        return jsonify({"status": "already processed"}), 200

    pro_until = _grant_pro(user, user_id)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET last_paid_payment_id = %s WHERE id = %s",
        (payment_id, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()

    print(f"Pro выдан пользователю {user_id} до {pro_until} (payment {payment_id})")

    return jsonify({"status": "ok"}), 200