# routes/payment.py

import os
import uuid
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash
)

from database import get_db
from rate import (
    PRO_DAYS,
    PRO_PRICE,
    has_pro_access,
    get_pro_offer
)


# ============================================================
# BLUEPRINT
# ============================================================

payment_bp = Blueprint(
    "payment",
    __name__,
    url_prefix="/payment"
)


# ============================================================
# ЮKASSA
# ============================================================

# Устанавливаются через переменные окружения:
#
# YOOKASSA_SHOP_ID
# YOOKASSA_SECRET_KEY
#
# Например в терминале:
#
# export YOOKASSA_SHOP_ID="..."
# export YOOKASSA_SECRET_KEY="..."

YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")


# ============================================================
# СТРАНИЦА ОПЛАТЫ
# ============================================================

@payment_bp.route("/")
def payment_page():
    """
    Страница оплаты Pro.
    """

    # Проверяем авторизацию
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("auth.login"))

    # Получаем информацию о Pro
    offer = get_pro_offer()

    return render_template(
        "payment.html",
        offer=offer
    )


# ============================================================
# СОЗДАНИЕ ПЛАТЕЖА
# ============================================================

@payment_bp.route("/create", methods=["POST"])
def create_payment():
    """
    Создаёт платёж в ЮKassa.
    """

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("auth.login"))

    # ========================================================
    # Если пользователь уже Pro
    # ========================================================

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        flash("Пользователь не найден.", "error")
        return redirect(url_for("main.home"))

    # Администратору платить не нужно
    if user.get("role") == "admin":
        flash("У администратора уже есть Pro.", "info")
        return redirect(url_for("main.home"))

    # Уже есть активный Pro
    if has_pro_access(user):
        flash("У вас уже активен тариф Pro.", "info")
        return redirect(url_for("main.home"))

    # ========================================================
    # Проверяем настройки ЮKassa
    # ========================================================

    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:

        flash(
            "Оплата пока не настроена. Добавьте данные ЮKassa.",
            "error"
        )

        return redirect(url_for("payment.payment_page"))

    # ========================================================
    # ЮKassa
    # ========================================================

    try:

        from yookassa import Configuration, Payment

        Configuration.account_id = YOOKASSA_SHOP_ID
        Configuration.secret_key = YOOKASSA_SECRET_KEY

        idempotence_key = str(uuid.uuid4())

        payment = Payment.create(
            {
                "amount": {
                    "value": f"{PRO_PRICE / 100:.2f}",
                    "currency": "RUB"
                },

                "capture": True,

                "confirmation": {
                    "type": "redirect",
                    "return_url": url_for(
                        "payment.payment_success",
                        _external=True
                    )
                },

                "description": (
                    f"Sinus Pro — {PRO_DAYS} дней"
                ),

                "metadata": {
                    "user_id": str(user_id),
                    "tariff": "pro"
                }
            },
            idempotence_key
        )

        # Сохраняем ID платежа
        payment_id = payment.id

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET last_payment_id = %s
            WHERE id = %s
            """,
            (payment_id, user_id)
        )

        conn.commit()

        cur.close()
        conn.close()

        # Получаем URL страницы оплаты
        confirmation_url = (
            payment.confirmation.confirmation_url
        )

        return redirect(confirmation_url)

    except Exception as e:

        print("Ошибка создания платежа:", e)

        flash(
            "Не удалось создать платёж. Попробуйте ещё раз.",
            "error"
        )

        return redirect(url_for("payment.payment_page"))


# ============================================================
# ВОЗВРАТ ПОСЛЕ ОПЛАТЫ
# ============================================================

@payment_bp.route("/success")
def payment_success():
    """
    Пользователь возвращается сюда после оплаты.

    ВАЖНО:
    Сам факт перехода на эту страницу НЕ означает,
    что платёж успешно завершён.

    Поэтому здесь дополнительно проверяем платёж через ЮKassa.
    """

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        return redirect(url_for("auth.login"))

    payment_id = user.get("last_payment_id")

    if not payment_id:
        flash(
            "Платёж не найден.",
            "error"
        )

        return redirect(url_for("main.home"))

    # ========================================================
    # Проверяем платёж в ЮKassa
    # ========================================================

    try:

        from yookassa import Configuration, Payment

        Configuration.account_id = YOOKASSA_SHOP_ID
        Configuration.secret_key = YOOKASSA_SECRET_KEY

        payment = Payment.find_one(payment_id)

        # Платёж действительно завершён
        if payment.status == "succeeded":

            # Проверяем сумму
            paid_amount = float(
                payment.amount.value
            )

            required_amount = PRO_PRICE / 100

            if paid_amount < required_amount:

                flash(
                    "Сумма платежа не соответствует тарифу.",
                    "error"
                )

                return redirect(
                    url_for("main.home")
                )

            # =================================================
            # Выдаём Pro
            # =================================================

            now = datetime.now()

            # Если старый Pro ещё действует,
            # продлеваем от его окончания.
            old_until = user.get("pro_until")

            if old_until and old_until > now:
                start_date = old_until
            else:
                start_date = now

            pro_until = start_date + timedelta(
                days=PRO_DAYS
            )

            conn = get_db()
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE users
                SET tariff = 'pro',
                    pro_until = %s
                WHERE id = %s
                """,
                (
                    pro_until,
                    user_id
                )
            )

            conn.commit()

            cur.close()
            conn.close()

            flash(
                "Оплата прошла успешно! Pro активирован.",
                "success"
            )

            return redirect(
                url_for("main.home")
            )

        elif payment.status == "pending":

            flash("Платёж ещё обрабатывается. "
                "Попробуйте обновить страницу немного позже.",
                "info"
            )

        else:

            flash(
                "Платёж не был завершён.",
                "error"
            )

    except Exception as e:

        print(
            "Ошибка проверки платежа:",
            e
        )

        flash(
            "Не удалось проверить статус платежа.",
            "error"
        )

    return redirect(
        url_for("main.home")
    )