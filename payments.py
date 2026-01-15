"""
Модуль оплаты для Узбекистана
Поддержка: Click, Payme, перевод на карту (Uzcard/Humo)
"""
import uuid
from datetime import datetime
import config
import database as db

# Хранилище ожидающих платежей
pending_payments: dict[str, dict] = {}


async def create_payment(user_id: int, plan: str, method: str) -> tuple[str, str]:
    """
    Создать платеж
    method: 'click', 'payme', 'card'
    Возвращает (payment_info, payment_id)
    """
    amount = config.PRICES.get(plan, config.PRICES["month"])
    payment_id = str(uuid.uuid4())[:8].upper()
    
    plan_names = {"week": "Неделя", "month": "Месяц", "year": "Год"}
    
    # Сохраняем информацию о платеже
    pending_payments[payment_id] = {
        "user_id": user_id,
        "plan": plan,
        "amount": amount,
        "method": method,
        "created_at": datetime.now(),
        "status": "pending"
    }
    
    # Сохраняем в БД
    await db.save_payment(user_id, payment_id, amount, plan, "pending")
    
    return payment_id, amount


def get_payment_instructions(method: str, amount: int, payment_id: str) -> str:
    """Получить инструкции по оплате"""
    
    if method == "click":
        return f"""
💳 <b>Оплата через Click</b>

💰 Сумма: <b>{amount:,} сум</b>
🔢 Номер заказа: <code>{payment_id}</code>

📱 <b>Как оплатить:</b>
1. Откройте приложение Click
2. Выберите "Оплата услуг"
3. Найдите <b>NeuralBot</b> или введите ID: <code>{config.CLICK_SERVICE_ID}</code>
4. Введите номер заказа: <code>{payment_id}</code>
5. Оплатите {amount:,} сум

После оплаты нажмите "✅ Я оплатил"
"""
    
    elif method == "payme":
        return f"""
💳 <b>Оплата через Payme</b>

💰 Сумма: <b>{amount:,} сум</b>
🔢 Номер заказа: <code>{payment_id}</code>

📱 <b>Как оплатить:</b>
1. Откройте приложение Payme
2. Выберите "Оплата услуг"
3. Найдите <b>NeuralBot</b>
4. Введите номер заказа: <code>{payment_id}</code>
5. Оплатите {amount:,} сум

После оплаты нажмите "✅ Я оплатил"
"""
    
    else:  # card
        return f"""
💳 <b>Перевод на карту</b>

💰 Сумма: <b>{amount:,} сум</b>
🔢 Номер заказа: <code>{payment_id}</code>

💳 <b>Реквизиты для перевода:</b>
├ Карта: <code>{config.CARD_NUMBER}</code>
├ Банк: {config.CARD_BANK}
└ Получатель: {config.CARD_HOLDER}

📝 <b>ВАЖНО:</b> В комментарии к переводу укажите:
<code>{payment_id}</code>

После перевода нажмите "✅ Я оплатил"
"""


async def request_payment_confirmation(payment_id: str) -> dict:
    """Запросить подтверждение платежа у админа"""
    if payment_id not in pending_payments:
        return {"success": False, "error": "Платеж не найден"}
    
    payment = pending_payments[payment_id]
    payment["status"] = "awaiting_confirmation"
    
    return {
        "success": True,
        "payment": payment
    }


async def confirm_payment(payment_id: str) -> tuple[bool, dict]:
    """
    Админ подтверждает платеж
    """
    if payment_id not in pending_payments:
        # Проверяем в БД
        return False, {"error": "Платеж не найден"}
    
    payment = pending_payments[payment_id]
    
    # Создаем подписку
    expires_at = await db.create_subscription(
        payment["user_id"],
        payment["plan"],
        payment_id,
        payment["amount"]
    )
    
    # Обновляем статус
    payment["status"] = "confirmed"
    await db.update_payment_status(payment_id, "succeeded")
    
    return True, {
        "user_id": payment["user_id"],
        "plan": payment["plan"],
        "amount": payment["amount"],
        "expires_at": expires_at
    }


async def reject_payment(payment_id: str) -> tuple[bool, int]:
    """Админ отклоняет платеж"""
    if payment_id not in pending_payments:
        return False, 0
    
    payment = pending_payments[payment_id]
    user_id = payment["user_id"]
    payment["status"] = "rejected"
    await db.update_payment_status(payment_id, "rejected")
    
    return True, user_id


def get_pending_payment(payment_id: str) -> dict:
    """Получить информацию о платеже"""
    return pending_payments.get(payment_id, {})
