"""
Модуль работы с базой данных
"""
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional
import config


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                referrer_id INTEGER,
                total_queries INTEGER DEFAULT 0,
                bonus_queries INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            )
        """)
        
        # Таблица подписок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                payment_id TEXT,
                amount INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица использования (для отслеживания дневного лимита)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query_date DATE,
                query_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, query_date)
            )
        """)
        
        # Таблица платежей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_id TEXT UNIQUE,
                amount INTEGER,
                plan TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    """Получить пользователя"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, username: str, first_name: str, referrer_id: int = None):
    """Создать пользователя"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, referrer_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, referrer_id))
        
        # Начисляем бонус рефереру
        if referrer_id:
            await db.execute("""
                UPDATE users SET bonus_queries = bonus_queries + ?
                WHERE user_id = ?
            """, (config.REFERRAL_BONUS, referrer_id))
        
        await db.commit()


async def get_today_usage(user_id: int) -> int:
    """Получить количество запросов за сегодня"""
    today = datetime.now().date()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT query_count FROM usage WHERE user_id = ? AND query_date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def increment_usage(user_id: int):
    """Увеличить счетчик использования"""
    today = datetime.now().date()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO usage (user_id, query_date, query_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, query_date) 
            DO UPDATE SET query_count = query_count + 1
        """, (user_id, today))
        
        await db.execute("""
            UPDATE users SET total_queries = total_queries + 1
            WHERE user_id = ?
        """, (user_id,))
        
        await db.commit()


async def use_bonus_query(user_id: int) -> bool:
    """Использовать бонусный запрос"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT bonus_queries FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] > 0:
                await db.execute(
                    "UPDATE users SET bonus_queries = bonus_queries - 1 WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
                return True
    return False


async def has_active_subscription(user_id: int) -> bool:
    """Проверить активную подписку"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("""
            SELECT expires_at FROM subscriptions 
            WHERE user_id = ? AND expires_at > datetime('now')
            ORDER BY expires_at DESC LIMIT 1
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_subscription_expires(user_id: int) -> Optional[str]:
    """Получить дату окончания подписки"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("""
            SELECT expires_at FROM subscriptions 
            WHERE user_id = ? AND expires_at > datetime('now')
            ORDER BY expires_at DESC LIMIT 1
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def create_subscription(user_id: int, plan: str, payment_id: str, amount: int):
    """Создать подписку"""
    duration = config.DURATIONS.get(plan, 30)
    expires_at = datetime.now() + timedelta(days=duration)
    
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO subscriptions (user_id, plan, expires_at, payment_id, amount)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, plan, expires_at, payment_id, amount))
        await db.commit()
    
    return expires_at


async def get_referral_count(user_id: int) -> int:
    """Получить количество рефералов"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def save_payment(user_id: int, payment_id: str, amount: int, plan: str, status: str):
    """Сохранить платеж"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO payments (user_id, payment_id, amount, plan, status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, payment_id, amount, plan, status))
        await db.commit()


async def update_payment_status(payment_id: str, status: str):
    """Обновить статус платежа"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "UPDATE payments SET status = ? WHERE payment_id = ?",
            (status, payment_id)
        )
        await db.commit()


async def get_stats() -> dict:
    """Получить статистику для админа"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Всего пользователей
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        
        # Premium подписчиков
        async with db.execute("""
            SELECT COUNT(DISTINCT user_id) FROM subscriptions 
            WHERE expires_at > datetime('now')
        """) as cursor:
            premium_users = (await cursor.fetchone())[0]
        
        # Запросов сегодня
        today = datetime.now().date()
        async with db.execute(
            "SELECT SUM(query_count) FROM usage WHERE query_date = ?", (today,)
        ) as cursor:
            row = await cursor.fetchone()
            today_queries = row[0] if row[0] else 0
        
        # Доход за месяц
        month_ago = datetime.now() - timedelta(days=30)
        async with db.execute("""
            SELECT SUM(amount) FROM subscriptions 
            WHERE started_at > ?
        """, (month_ago,)) as cursor:
            row = await cursor.fetchone()
            monthly_revenue = row[0] if row[0] else 0
        
        # Новых за сегодня
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(registered_at) = ?", (today,)
        ) as cursor:
            new_today = (await cursor.fetchone())[0]
        
        # Новых за неделю
        week_ago = datetime.now() - timedelta(days=7)
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE registered_at > ?", (week_ago,)
        ) as cursor:
            new_week = (await cursor.fetchone())[0]
        
        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "today_queries": today_queries,
            "monthly_revenue": monthly_revenue,
            "new_today": new_today,
            "new_week": new_week
        }
