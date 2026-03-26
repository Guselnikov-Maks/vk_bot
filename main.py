import os
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text

from database import Database

# Загрузка .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv('VK_TOKEN')
if not TOKEN:
    raise ValueError("VK_TOKEN not found")

# Инициализация
bot = Bot(token=TOKEN)
db = Database()

# Клавиатура
main_keyboard = (
    Keyboard()
    .add(Text("➕ Добавить заправку"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("📊 Мой пробег"), color=KeyboardButtonColor.PRIMARY)
    .row()
    .add(Text("📋 Список заправок"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("🤔 Думаю"), color=KeyboardButtonColor.PRIMARY)
    .row()
    .add(Text("❓ Помощь"), color=KeyboardButtonColor.SECONDARY)
)

user_states = {}

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
async def ensure_registered(vk_id: int, message: Message) -> bool:
    """Проверяет регистрацию, если нет — запускает процесс регистрации"""
    is_registered = await asyncio.to_thread(db.check_user_exists, vk_id)
    if not is_registered:
        user_states[vk_id] = "awaiting_login"
        await message.answer(
            "🔐 Вы не зарегистрированы.\n"
            "Для регистрации введите команду 'регистрация' или просто введите логин."
        )
        return False
    return True

# ---------- ОБРАБОТЧИКИ ----------
@bot.on.message(text=["начать", "start", "Начать"])
async def start_command(message: Message):
    await message.answer(
        "👋 Привет! Я бот для учёта заправок и пробега.\n"
        "Для начала работы отправьте команду 'регистрация'.\n"
        "Я буду хранить ваши данные и помогу отслеживать расход топлива."
    )

@bot.on.message(text="регистрация")
async def registration_command(message: Message):
    vk_id = message.from_id
    # Проверяем, не зарегистрирован ли уже
    is_registered = await asyncio.to_thread(db.check_user_exists, vk_id)
    if is_registered:
        await message.answer("✅ Вы уже зарегистрированы. Используйте кнопки меню.", keyboard=main_keyboard) # type: ignore
        return

    # Запускаем процесс регистрации
    user_states[vk_id] = "awaiting_login"
    await message.answer(
        "🔐 Начинаем регистрацию.\n"
        "Введите ваш ЛОГИН от сайта:"
    )

@bot.on.message(text="❓ Помощь")
async def help_command(message: Message):
    help_text = (
        "📖 **Справка по боту**\n\n"
        "1. Регистрация: отправьте 'регистрация', затем логин и пароль от сайта.\n"
        "2. После успешной авторизации вы сможете:\n"
        "   • ➕ Добавить заправку — указать объём топлива который вы залили\n"
        "   • 📊 Мой пробег — получить текущий пробег с сайта и расчёт\n"
        "   • 📋 Список заправок — все ваши записи за этот месяц\n"
        "3. Если забыли данные, напишите 'данные' — я пришлю сохранённые логин/пароль.\n\n"
        "⚠️ При проблемах с авторизацией обратитесь к администратору."
    )
    await message.answer(help_text, keyboard=main_keyboard) # type: ignore

@bot.on.message(text="➕ Добавить заправку")
async def add_refuel_command(message: Message):
    vk_id = message.from_id
    if not await ensure_registered(vk_id, message):
        return
    user_states[vk_id] = "awaiting_value"
    await message.answer("⛽ Введите количество литров (целое число):", keyboard=None)

@bot.on.message(text="📊 Мой пробег")
async def show_mileage_command(message: Message):
    vk_id = message.from_id
    if not await ensure_registered(vk_id, message):
        return

    # Здесь будет вызов парсера сайта (site_parser.py)
    # Пока заглушка
    await message.answer(
        "📊 Функция в разработке.\n"
        "Скоро здесь будет расчёт пробега и эффективности.",
        keyboard=main_keyboard # type: ignore
    )

@bot.on.message(text="📋 Список заправок")
async def show_refuels_list(message: Message):
    vk_id = message.from_id
    if not await ensure_registered(vk_id, message):
        return

    monthly_data = await asyncio.to_thread(db.get_monthly_values, vk_id)
    
    if not monthly_data['values']:
        current_month = datetime.now().strftime('%B %Y')
        await message.answer(
            f"📭 За {current_month} пока нет заправок.\n"
            f"Добавьте первую через '➕ Добавить заправку'.",
            keyboard=main_keyboard # type: ignore
        )
        return

    # Формируем сообщение
    current_month = datetime.now().strftime('%B %Y')
    result = f"📋 **Заправки за {current_month}**\n\n"
    
    for row in monthly_data['values']:
        created_at = row['created_at']
        formatted_date = created_at.strftime("%d.%m.%Y %H:%M")
        result += f"• {row['value']} л — {formatted_date}\n"
    
    result += f"\n📊 **Итого за месяц: {monthly_data['total']} литров**"
    
    await message.answer(result, keyboard=main_keyboard) # type: ignore

@bot.on.message(text="данные")
async def show_user_data(message: Message):
    vk_id = message.from_id
    user_data = await asyncio.to_thread(db.get_user_credentials, vk_id)
    if not user_data:
        await message.answer("❌ Вы не зарегистрированы.")
        return
    await message.answer(
        f"🔐 Ваши данные:\n"
        f"Логин: {user_data['login']}\n\n"
        f"Пароль хранится в зашифрованном виде.\n"
        f"При необходимости сбросить пароль - обратитесь к администратору."
    )

@bot.on.message()
async def handle_messages(message: Message):
    vk_id = message.from_id
    text = message.text
    state = user_states.get(vk_id)

    if state == "awaiting_login":
        user_states[vk_id] = "awaiting_password"
        user_states[f"{vk_id}_login"] = text
        await message.answer("Введите ваш ПАРОЛЬ от сайта:")

    elif state == "awaiting_password":
        login = user_states.pop(f"{vk_id}_login", None)
        password = text

        if login and password:
            # Здесь позже добавим проверку авторизации на сайте
            success = await asyncio.to_thread(db.register_user, vk_id, login, password)
            if success:
                user_states.pop(vk_id, None)
                await message.answer(
                    "✅ Регистрация успешна!\n"
                    "Данные сохранены. Используйте кнопки меню.",
                    keyboard=main_keyboard # type: ignore
                )
            else:
                user_states.pop(vk_id, None)
                await message.answer(
                    "❌ Ошибка: пользователь уже зарегистрирован.\n"
                    "Если это не так, обратитесь к администратору."
                )

    elif state == "awaiting_value":
        try:
            value = int(text)
            if value <= 0:
                raise ValueError()
            today = datetime.now().strftime("%Y-%m-%d")
            success = await asyncio.to_thread(db.add_value, vk_id, value, today)
            if success:
                user_states.pop(vk_id, None)
                await message.answer(f"✅ Заправка {value} л добавлена!", keyboard=main_keyboard) # type: ignore
            else:
                await message.answer("❌ Ошибка при сохранении заправки.")
        except ValueError:
            await message.answer("❌ Введите положительное целое число литров.")
    else:
        # Если нет активного состояния — просто подсказываем
        await message.answer(
            "Используйте кнопки меню или команду 'регистрация'.",
            keyboard=main_keyboard # type: ignore
        )

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    try:
        # Проверка БД
        if db.check_user_exists(1):
            print("✅ Database connection OK")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        exit(1)

    print("🤖 Бот запущен!")
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")