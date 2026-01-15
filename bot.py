"""
NeuralBot - AI-ассистент в Telegram с монетизацией
Главный модуль бота (версия для Узбекистана)
"""
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
import database as db
from keyboards import (
    get_main_keyboard, 
    get_subscription_keyboard, 
    get_payment_method_keyboard,
    get_payment_confirm_keyboard,
    get_admin_confirm_keyboard,
    get_limit_keyboard,
    get_admin_keyboard
)
from ai_service import get_ai_response, clear_history
import payments

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ==================== КОМАНДЫ ====================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "Пользователь"
    
    # Проверяем реферальную ссылку
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        try:
            ref_code = message.text.split()[1]
            if ref_code.startswith("ref"):
                referrer_id = int(ref_code[3:])
                if referrer_id == user_id:
                    referrer_id = None
        except:
            pass
    
    # Создаем пользователя
    await db.create_user(user_id, username, first_name, referrer_id)
    
    # Уведомляем реферера
    if referrer_id:
        try:
            await bot.send_message(
                referrer_id,
                f"🎉 По вашей ссылке присоединился новый пользователь!\n"
                f"Вам начислено <b>+{config.REFERRAL_BONUS} запросов</b>!"
            )
        except:
            pass
    
    welcome_text = config.TEXTS["welcome"].format(
        free_queries=config.FREE_QUERIES_PER_DAY
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@dp.message(Command("help"))
@dp.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    """Справка по боту"""
    help_text = """
<b>❓ Справка по NeuralBot</b>

<b>Как пользоваться:</b>
Просто напишите любой вопрос, и я отвечу!

<b>Команды:</b>
/start — Перезапустить бота
/profile — Ваш профиль
/premium — Подписка Premium
/referral — Пригласить друга
/clear — Очистить контекст диалога
/help — Эта справка

<b>Что я умею:</b>
• Отвечать на вопросы
• Писать тексты и статьи
• Помогать с программированием
• Переводить тексты
• Генерировать идеи

<b>Способы оплаты:</b>
📱 Click, Payme
💳 Uzcard, Humo

<b>Поддержка:</b> @your_support_username
"""
    await message.answer(help_text)


@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    """Очистка истории диалога"""
    clear_history(message.from_user.id)
    await message.answer("🗑 История диалога очищена. Начнем с чистого листа!")


@dp.message(Command("profile"))
@dp.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message):
    """Профиль пользователя"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Профиль не найден. Используйте /start")
        return
    
    has_premium = await db.has_active_subscription(user_id)
    expires = await db.get_subscription_expires(user_id)
    
    today_usage = await db.get_today_usage(user_id)
    remaining = config.FREE_QUERIES_PER_DAY - today_usage + user.get("bonus_queries", 0)
    if has_premium:
        remaining = "∞"
    
    reg_date = user.get("registered_at", "")
    if reg_date:
        try:
            dt = datetime.fromisoformat(reg_date)
            reg_date = dt.strftime("%d.%m.%Y")
        except:
            reg_date = "—"
    
    subscription_status = "💎 Premium активна" if has_premium else "❌ Нет подписки"
    subscription_expires = ""
    if expires:
        try:
            dt = datetime.fromisoformat(expires)
            subscription_expires = f"\n📅 Действует до: {dt.strftime('%d.%m.%Y %H:%M')}"
        except:
            pass
    
    referrals = await db.get_referral_count(user_id)
    
    profile_text = config.TEXTS["profile"].format(
        user_id=user_id,
        reg_date=reg_date,
        total_queries=user.get("total_queries", 0),
        remaining=remaining,
        subscription_status=subscription_status,
        subscription_expires=subscription_expires,
        referrals=referrals
    )
    
    await message.answer(profile_text)


@dp.message(Command("premium"))
@dp.message(F.text == "💎 Premium")
async def cmd_premium(message: Message):
    """Информация о подписке"""
    subscription_text = config.TEXTS["subscription_info"].format(
        price_week=config.PRICES["week"],
        price_month=config.PRICES["month"],
        price_year=config.PRICES["year"]
    )
    await message.answer(subscription_text, reply_markup=get_subscription_keyboard())


@dp.message(Command("referral"))
@dp.message(F.text == "🎁 Пригласить друга")
async def cmd_referral(message: Message):
    """Реферальная программа"""
    user_id = message.from_user.id
    
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{user_id}"
    
    referral_count = await db.get_referral_count(user_id)
    bonus_queries = referral_count * config.REFERRAL_BONUS
    
    referral_text = config.TEXTS["referral_info"].format(
        ref_link=ref_link,
        ref_count=referral_count,
        bonus_queries=bonus_queries,
        referral_bonus=config.REFERRAL_BONUS
    )
    
    await message.answer(referral_text)


# ==================== АДМИН КОМАНДЫ ====================

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ панель"""
    if message.from_user.id != config.ADMIN_ID:
        return
    
    await message.answer("🔐 <b>Админ панель</b>", reply_markup=get_admin_keyboard())


@dp.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика для админа"""
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    stats = await db.get_stats()
    
    stats_text = config.TEXTS["admin_stats"].format(**stats)
    await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())
    await callback.answer()


# ==================== ОПЛАТА ====================

@dp.callback_query(F.data == "subscription")
async def callback_subscription(callback: CallbackQuery):
    """Показать подписки"""
    subscription_text = config.TEXTS["subscription_info"].format(
        price_week=config.PRICES["week"],
        price_month=config.PRICES["month"],
        price_year=config.PRICES["year"]
    )
    await callback.message.edit_text(
        subscription_text, 
        reply_markup=get_subscription_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("buy:"))
async def callback_buy(callback: CallbackQuery):
    """Выбор тарифа - показать способы оплаты"""
    plan = callback.data.split(":")[1]
    
    plan_names = {"week": "Неделя", "month": "Месяц", "year": "Год"}
    price = config.PRICES.get(plan, 0)
    
    text = f"""
💎 <b>Оформление подписки</b>

📦 Тариф: <b>{plan_names.get(plan, plan)}</b>
💰 Стоимость: <b>{price:,} сум</b>

Выберите способ оплаты 👇
"""
    await callback.message.edit_text(text, reply_markup=get_payment_method_keyboard(plan))
    await callback.answer()


@dp.callback_query(F.data.startswith("pay:"))
async def callback_pay(callback: CallbackQuery):
    """Обработка выбора способа оплаты"""
    parts = callback.data.split(":")
    plan = parts[1]
    method = parts[2]
    user_id = callback.from_user.id
    
    # Создаем платеж
    payment_id, amount = await payments.create_payment(user_id, plan, method)
    
    # Получаем инструкции
    instructions = payments.get_payment_instructions(method, amount, payment_id)
    
    await callback.message.edit_text(
        instructions,
        reply_markup=get_payment_confirm_keyboard(payment_id)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("paid:"))
async def callback_paid(callback: CallbackQuery):
    """Пользователь нажал 'Я оплатил'"""
    payment_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    result = await payments.request_payment_confirmation(payment_id)
    
    if not result["success"]:
        await callback.answer("Платеж не найден", show_alert=True)
        return
    
    payment = result["payment"]
    
    # Уведомляем пользователя
    await callback.message.edit_text(
        f"⏳ <b>Заявка на оплату отправлена!</b>\n\n"
        f"🔢 Номер заказа: <code>{payment_id}</code>\n"
        f"💰 Сумма: {payment['amount']:,} сум\n\n"
        f"Ожидайте подтверждения. Обычно это занимает 5-15 минут."
    )
    
    # Отправляем заявку админу
    method_names = {"click": "Click", "payme": "Payme", "card": "Карта"}
    plan_names = {"week": "Неделя", "month": "Месяц", "year": "Год"}
    
    admin_text = f"""
🔔 <b>Новая заявка на оплату!</b>

👤 Пользователь: <code>{user_id}</code>
📦 Тариф: {plan_names.get(payment['plan'], payment['plan'])}
💰 Сумма: <b>{payment['amount']:,} сум</b>
💳 Способ: {method_names.get(payment['method'], payment['method'])}
🔢 Номер заказа: <code>{payment_id}</code>

Проверьте поступление и подтвердите 👇
"""
    
    try:
        await bot.send_message(
            config.ADMIN_ID,
            admin_text,
            reply_markup=get_admin_confirm_keyboard(payment_id)
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
    
    await callback.answer("✅ Заявка отправлена!")


@dp.callback_query(F.data.startswith("admin_confirm:"))
async def admin_confirm_payment(callback: CallbackQuery):
    """Админ подтверждает платеж"""
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    payment_id = callback.data.split(":")[1]
    
    success, result = await payments.confirm_payment(payment_id)
    
    if success:
        # Уведомляем пользователя
        expires_str = result["expires_at"].strftime("%d.%m.%Y %H:%M")
        
        try:
            await bot.send_message(
                result["user_id"],
                f"✅ <b>Оплата подтверждена!</b>\n\n"
                f"Ваша Premium подписка активирована.\n"
                f"📅 Действует до: {expires_str}\n\n"
                f"Наслаждайтесь безлимитным доступом! 🚀"
            )
        except:
            pass
        
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>ПОДТВЕРЖДЕНО</b>"
        )
        await callback.answer("✅ Платеж подтвержден!")
    else:
        await callback.answer("❌ Ошибка подтверждения", show_alert=True)


@dp.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_payment(callback: CallbackQuery):
    """Админ отклоняет платеж"""
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    payment_id = callback.data.split(":")[1]
    
    success, user_id = await payments.reject_payment(payment_id)
    
    if success:
        # Уведомляем пользователя
        try:
            await bot.send_message(
                user_id,
                f"❌ <b>Оплата не подтверждена</b>\n\n"
                f"Номер заказа: <code>{payment_id}</code>\n\n"
                f"Если вы уверены, что оплатили — свяжитесь с поддержкой."
            )
        except:
            pass
        
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ <b>ОТКЛОНЕНО</b>"
        )
        await callback.answer("❌ Платеж отклонен")
    else:
        await callback.answer("Ошибка", show_alert=True)


@dp.callback_query(F.data == "referral")
async def callback_referral(callback: CallbackQuery):
    """Реферальная программа через callback"""
    user_id = callback.from_user.id
    
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{user_id}"
    
    referral_count = await db.get_referral_count(user_id)
    bonus_queries = referral_count * config.REFERRAL_BONUS
    
    referral_text = config.TEXTS["referral_info"].format(
        ref_link=ref_link,
        ref_count=referral_count,
        bonus_queries=bonus_queries,
        referral_bonus=config.REFERRAL_BONUS
    )
    
    await callback.message.edit_text(referral_text, reply_markup=get_subscription_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "menu")
async def callback_menu(callback: CallbackQuery):
    """Возврат в меню"""
    welcome_text = config.TEXTS["welcome"].format(
        free_queries=config.FREE_QUERIES_PER_DAY
    )
    await callback.message.edit_text(welcome_text)
    await callback.answer()


# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================

@dp.message(F.text)
async def handle_message(message: Message):
    """Обработка текстовых сообщений (AI)"""
    user_id = message.from_user.id
    user_text = message.text
    
    # Проверяем пользователя
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(
            user_id, 
            message.from_user.username or "", 
            message.from_user.first_name or ""
        )
    
    # Проверяем подписку
    has_premium = await db.has_active_subscription(user_id)
    
    if not has_premium:
        today_usage = await db.get_today_usage(user_id)
        user_data = await db.get_user(user_id)
        bonus = user_data.get("bonus_queries", 0) if user_data else 0
        
        if today_usage >= config.FREE_QUERIES_PER_DAY and bonus <= 0:
            limit_text = config.TEXTS["limit_reached"].format(
                free_queries=config.FREE_QUERIES_PER_DAY,
                referral_bonus=config.REFERRAL_BONUS
            )
            await message.answer(limit_text, reply_markup=get_limit_keyboard())
            return
        
        if today_usage >= config.FREE_QUERIES_PER_DAY:
            await db.use_bonus_query(user_id)
    
    # Показываем "печатает..."
    await bot.send_chat_action(user_id, "typing")
    
    # Получаем ответ от AI
    response = await get_ai_response(user_id, user_text)
    
    # Увеличиваем счетчик
    await db.increment_usage(user_id)
    
    # Отправляем ответ
    await message.answer(response)


# ==================== ЗАПУСК ====================

async def main():
    """Запуск бота"""
    logger.info("Initializing database...")
    await db.init_db()
    
    logger.info("Starting NeuralBot (Uzbekistan version)...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
