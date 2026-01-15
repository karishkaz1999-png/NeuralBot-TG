"""
Сервис интеграции с OpenAI
"""
from openai import AsyncOpenAI
import config

# Ленивая инициализация клиента
_client = None

def get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client

# Системный промпт для бота
SYSTEM_PROMPT = """Ты — NeuralBot, дружелюбный и умный AI-ассистент в Telegram.
Твоя задача — помогать пользователям с любыми вопросами.

Правила:
1. Отвечай на русском языке, если пользователь пишет на русском
2. Будь вежливым и дружелюбным
3. Давай точные и полезные ответы
4. Если не знаешь ответ — честно скажи об этом
5. Используй эмодзи для выразительности, но в меру
6. Форматируй длинные ответы для удобства чтения

Ты можешь помогать с:
- Написанием текстов, статей, постов
- Программированием и кодом
- Переводами
- Аналитикой и исследованиями
- Креативными задачами
- Любыми вопросами пользователей"""


# Хранение контекста диалогов (в памяти)
conversation_history: dict[int, list] = {}


async def get_ai_response(user_id: int, message: str) -> str:
    """Получить ответ от AI"""
    try:
        # Получаем или создаем историю диалога
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        history = conversation_history[user_id]
        
        # Добавляем сообщение пользователя
        history.append({"role": "user", "content": message})
        
        # Ограничиваем историю последними 10 сообщениями
        if len(history) > 20:
            history = history[-20:]
            conversation_history[user_id] = history
        
        # Формируем сообщения для API
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        
        # Запрос к OpenAI
        response = await get_client().chat.completions.create(
            model=config.GPT_MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content
        
        # Добавляем ответ в историю
        history.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
        
    except Exception as e:
        return f"❌ Произошла ошибка: {str(e)}\n\nПопробуйте еще раз или обратитесь в поддержку."


def clear_history(user_id: int):
    """Очистить историю диалога"""
    if user_id in conversation_history:
        del conversation_history[user_id]
