"""
Клавиатуры для бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import config


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💎 Premium"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🎁 Пригласить друга"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора подписки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🔹 Неделя — {config.PRICES['week']:,} сум",
            callback_data="buy:week"
        )],
        [InlineKeyboardButton(
            text=f"🔹 Месяц — {config.PRICES['month']:,} сум (выгодно!)",
            callback_data="buy:month"
        )],
        [InlineKeyboardButton(
            text=f"🔹 Год — {config.PRICES['year']:,} сум (супер!)",
            callback_data="buy:year"
        )],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="referral")]
    ])
    return keyboard


def get_payment_method_keyboard(plan: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Click", callback_data=f"pay:{plan}:click")],
        [InlineKeyboardButton(text="📱 Payme", callback_data=f"pay:{plan}:payme")],
        [InlineKeyboardButton(text="💳 Карта (Uzcard/Humo)", callback_data=f"pay:{plan}:card")],
        [InlineKeyboardButton(text="« Назад", callback_data="subscription")]
    ])
    return keyboard


def get_payment_confirm_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{payment_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="subscription")]
    ])
    return keyboard


def get_admin_confirm_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для админа - подтверждение платежа"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm:{payment_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject:{payment_id}")
        ]
    ])
    return keyboard


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад", callback_data="menu")]
    ])
    return keyboard


def get_limit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при исчерпании лимита"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Получить Premium", callback_data="subscription")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="referral")]
    ])
    return keyboard


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админ клавиатура"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")],
        [InlineKeyboardButton(text="👤 Найти пользователя", callback_data="admin:find_user")]
    ])
    return keyboard
