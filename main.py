import os
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text

from database import Database
from site_parser import SiteParser
from logger import setup_logger

# Загрузка .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Настройка логгера для бота
bot_logger = setup_logger('bot', 'bot.log')

TOKEN = os.getenv('VK_TOKEN')
if not TOKEN:
    bot_logger.error("VK_TOKEN not found in .env file")
    raise ValueError("VK_TOKEN not found")

# Инициализация
bot = Bot(token=TOKEN)
db = Database()
parser = SiteParser(excel_dir='excel_reports')

bot_logger.info("Bot initialized")

# Клавиатура
main_keyboard = (
    Keyboard()
    .add(Text("➕ Добавить заправку"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("📊 Мой пробег"), color=KeyboardButtonColor.PRIMARY)
    .row()
    .add(Text("📋 Список заправок"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("🔄 Получить отчет Excel"), color=KeyboardButtonColor.PRIMARY)
    .row()
    .add(Text("❓ Помощь"), color=KeyboardButtonColor.SECONDARY)
)

user_states = {}

async def ensure_registered(vk_id: int, message: Message) -> bool:
    """Проверяет регистрацию, если нет — запускает процесс регистрации"""
    is_registered = await asyncio.to_thread(db.check_user_exists, vk_id)
    if not is_registered:
        user_states[vk_id] = "awaiting_login"
        await message.answer(
            "🔐 Вы не зарегистрированы.\n"
            "Для регистрации введите команду 'регистрация' или просто введите логин."
        )
        bot_logger.debug(f"User {vk_id} not registered, starting registration")
        return False
    return True

# Обработчики
@bot.on.message(text=["начать", "start", "Начать"])
async def start_command(message: Message):
    vk_id = message.from_id
    bot_logger.info(f"Start command from user {vk_id}")
    await message.answer(
        "👋 Привет! Я бот для учёта заправок и пробега.\n"
        "Для начала работы отправьте команду 'регистрация'.\n"
        "Я буду хранить ваши данные и помогу отслеживать расход топлива.\n\n"
        "📐 Норма расхода: **10 литров = 100 км**"
    )

@bot.on.message(text="регистрация")
async def registration_command(message: Message):
    vk_id = message.from_id
    bot_logger.info(f"Registration command from user {vk_id}")
    is_registered = await asyncio.to_thread(db.check_user_exists, vk_id)
    if is_registered:
        await message.answer("✅ Вы уже зарегистрированы. Используйте кнопки меню.", keyboard=main_keyboard) # type: ignore
        return
    
    user_states[vk_id] = "awaiting_login"
    await message.answer(
        "🔐 Начинаем регистрацию.\n"
        "Введите ваш ЛОГИН от сайта:"
    )

@bot.on.message(text="❓ Помощь")
async def help_command(message: Message):
    vk_id = message.from_id
    bot_logger.info(f"Help command from user {vk_id}")
    help_text = (
        "📖 **Справка по боту**\n\n"
        "📐 **Норма расхода:** 10 литров = 100 км\n\n"
        "1. **Регистрация:** отправьте 'регистрация', затем логин и пароль от сайта.\n\n"
        "2. После успешной авторизации вы сможете:\n"
        "   • ➕ **Добавить заправку** — указать объём топлива\n"
        "   • 📊 **Мой пробег** — получить пробег с сайта и расчет эффективности\n"
        "   • 📋 **Список заправок** — все ваши записи за месяц\n"
        "   • 🔄 **Получить отчет Excel** — скачать подробный отчет\n\n"
        "3. **Как это работает:**\n"
        "   - Вы заправляетесь и добавляете литры в бота\n"
        "   - Бот получает пробег с сайта\n"
        "   - Сравнивает фактический пробег с ожидаемым (10 л/100 км)\n"
        "   - Показывает: вы в ПЛЮСЕ (экономия) или в МИНУСЕ (перерасход)\n\n"
        "4. Если забыли данные, напишите 'данные' — я пришлю сохранённый логин и пароль.\n\n"
        "⚠️ При проблемах с авторизацией обратитесь к администратору."
    )
    await message.answer(help_text, keyboard=main_keyboard) # type: ignore

@bot.on.message(text="➕ Добавить заправку")
async def add_refuel_command(message: Message):
    vk_id = message.from_id
    bot_logger.info(f"Add refuel command from user {vk_id}")
    if not await ensure_registered(vk_id, message):
        return
    user_states[vk_id] = "awaiting_value"
    await message.answer(
        "⛽ Введите количество литров (целое число):\n"
        "Например: 50\n\n"
        "💡 **Подсказка:** 10 литров = 100 км пробега",
        keyboard=None
    )

@bot.on.message(text="📊 Мой пробег")
async def show_mileage_command(message: Message):
    vk_id = message.from_id
    bot_logger.info(f"Mileage request from user {vk_id}")
    
    if not await ensure_registered(vk_id, message):
        return
    
    await message.answer("🔄 Получаю данные с сайта... Это может занять несколько минут.")
    
    user_data = await asyncio.to_thread(db.get_user_credentials, vk_id)
    if not user_data or not user_data.get('password'):
        bot_logger.warning(f"No credentials found for user {vk_id}")
        await message.answer("❌ Ошибка: не найдены данные пользователя.")
        return
    
    result = await asyncio.to_thread(
        parser.get_total_km, 
        user_data['login'], 
        user_data['password']
    )
    
    if not result['success']:
        await message.answer(
            f"❌ Ошибка при получении пробега:\n{result['message']}",
            keyboard=main_keyboard # type: ignore
        )
        return
    
    monthly_fuel = await asyncio.to_thread(db.get_monthly_total, vk_id)
    bot_logger.info(f"User {vk_id}: mileage={result['total_km']}, fuel={monthly_fuel}")
    
    if monthly_fuel == 0:
        await message.answer(
            f"📊 **Ваши данные:**\n\n"
            f"📈 Фактический пробег: {result['total_km']} км\n"
            f"⛽ Заправлено за месяц: 0 л\n\n"
            f"⚠️ Нет данных о заправках за месяц.\n"
            f"Добавьте заправки через '➕ Добавить заправку'.\n\n"
            f"📝 Количество записей пробега: {result['records_count']}",
            keyboard=main_keyboard # type: ignore
        )
        return
    
    expected_km = monthly_fuel * 10
    km_difference = result['total_km'] - expected_km
    fuel_difference = km_difference / 10
    
    if km_difference > 0:
        status = "✅ ПЛЮС"
        status_text = f"Вы проехали на {km_difference:.0f} км БОЛЬШЕ нормы!"
        fuel_text = f"💰 Экономия топлива: {fuel_difference:.1f} литров"
    elif km_difference < 0:
        status = "⚠️ МИНУС"
        status_text = f"Вы проехали на {abs(km_difference):.0f} км МЕНЬШЕ нормы!"
        fuel_text = f"📉 Перерасход топлива: {abs(fuel_difference):.1f} литров"
    else:
        status = "⚖️ НОЛЬ"
        status_text = "Вы точно уложились в норму!"
        fuel_text = "Расход топлива строго по норме"
    
    response = (
        f"📊 **Отчет по топливу**\n\n"
        f"📈 **Фактический пробег:** {result['total_km']} км\n"
        f"⛽ **Заправлено за месяц:** {monthly_fuel} л\n"
        f"📐 **Норма:** 10 л/100 км\n\n"
        f"🎯 **Ожидаемый пробег:** {expected_km} км\n"
        f"📊 **Разница:** {km_difference:+.0f} км\n\n"
        f"{status} {status_text}\n"
        f"{fuel_text}\n\n"
        f"📝 **Количество записей пробега:** {result['records_count']}"
    )
    
    await message.answer(response, keyboard=main_keyboard) # type: ignore

@bot.on.message(text="📋 Список заправок")
async def show_refuels_list(message: Message):
    vk_id = message.from_id
    bot_logger.info(f"Refuel list request from user {vk_id}")
    
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
    
    current_month = datetime.now().strftime('%B %Y')
    total_fuel = monthly_data['total']
    expected_km = total_fuel * 10
    
    result = f"📋 **Заправки за {current_month}**\n\n"
    
    for row in monthly_data['values']:
        created_at = row['created_at']
        formatted_date = created_at.strftime("%d.%m.%Y %H:%M")
        result += f"• {row['value']} л — {formatted_date}\n"
    
    result += f"\n📊 **Итого за месяц:** {total_fuel} л"
    result += f"\n🎯 **Ожидаемый пробег:** {expected_km} км (10 л/100 км)"
    
    await message.answer(result, keyboard=main_keyboard) # type: ignore

@bot.on.message(text="🔄 Получить отчет Excel")
async def get_excel_report(message: Message):
    vk_id = message.from_id
    bot_logger.info(f"Excel report request from user {vk_id}")
    
    if not await ensure_registered(vk_id, message):
        return
    
    await message.answer("🔄 Формирую Excel отчет... Это может занять некоторое время.")
    
    user_data = await asyncio.to_thread(db.get_user_credentials, vk_id)
    if not user_data or not user_data.get('password'):
        bot_logger.warning(f"No credentials found for user {vk_id}")
        await message.answer("❌ Ошибка: не найдены данные пользователя.")
        return
    
    result = await asyncio.to_thread(
        parser.get_mileage_report,
        user_data['login'],
        user_data['password'],
        message.from_id
    )
    
    if result['success']:
        try:
            # Получаем сервер для загрузки
            upload_server = await bot.api.docs.get_messages_upload_server(
                type='doc',
                peer_id=message.peer_id
            )
            
            # Загружаем файл
            async with aiohttp.ClientSession() as session:
                with open(result['filepath'], 'rb') as f:
                    form = aiohttp.FormData()
                    form.add_field('file', f, filename=result['filename'])
                    async with session.post(upload_server.upload_url, data=form) as resp:
                        file_data = await resp.json()
            
            # Сохраняем документ
            doc = await bot.api.docs.save(file=file_data['file'], title=result['filename'])
            
            # Отправляем сообщение с файлом
            await message.answer(
                f"✅ Отчет сформирован!\n"
                f"📊 Всего записей: {result['records_count']}\n"
                f"📈 Общий пробег: {result['total_km']} км\n"
                f"⛽ При норме 10 л/100 км вы бы потратили: {result['total_km'] / 10:.1f} литров",
                attachment=f"doc{doc.doc.owner_id}_{doc.doc.id}" # type: ignore
            )
            
            bot_logger.info(f"Excel report sent to user {vk_id}: {result['filename']}")
            
        except Exception as e:
            bot_logger.error(f"Failed to send Excel file to user {vk_id}: {e}")
            await message.answer(f"❌ Ошибка при отправке файла: {str(e)}")
        
        finally:
            try:
                os.remove(result['filepath'])
                bot_logger.debug(f"Temporary file removed: {result['filepath']}")
            except Exception as e:
                bot_logger.warning(f"Failed to remove temp file: {e}")
    else:
        bot_logger.error(f"Excel report failed for user {vk_id}: {result['message']}")
        await message.answer(f"❌ Ошибка при формировании отчета:\n{result['message']}")

@bot.on.message(text="данные")
async def show_user_data(message: Message):
    vk_id = message.from_id
    bot_logger.info(f"User data request from {vk_id}")
    user_data = await asyncio.to_thread(db.get_user_credentials, vk_id)
    if not user_data:
        await message.answer("❌ Вы не зарегистрированы.")
        return
    
    if user_data.get('password'):
        await message.answer(
            f"🔐 **Ваши данные:**\n\n"
            f"📝 Логин: {user_data['login']}\n"
            f"🔑 Пароль: {user_data['password']}\n\n"
            f"⚠️ Никому не передавайте эти данные!\n\n"
            f"📐 Норма расхода: 10 литров = 100 км"
        )
    else:
        await message.answer(
            f"🔐 **Ваши данные:**\n\n"
            f"📝 Логин: {user_data['login']}\n\n"
            f"⚠️ Пароль не может быть расшифрован. Обратитесь к администратору."
        )

@bot.on.message()
async def handle_messages(message: Message):
    vk_id = message.from_id
    text = message.text
    state = user_states.get(vk_id)
    
    if state == "awaiting_login":
        bot_logger.debug(f"User {vk_id} entered login")
        user_states[vk_id] = "awaiting_password"
        user_states[f"{vk_id}_login"] = text
        await message.answer("Введите ваш ПАРОЛЬ от сайта:")
    
    elif state == "awaiting_password":
        login = user_states.pop(f"{vk_id}_login", None)
        password = text
        
        if login and password:
            bot_logger.info(f"User {vk_id} attempting registration with login: {login}")
            await message.answer("🔄 Проверяю авторизацию на сайте...")
            auth_result = await asyncio.to_thread(parser.test_auth, login, password)
            
            if auth_result['success']:
                success = await asyncio.to_thread(db.register_user, vk_id, login, password)
                if success:
                    user_states.pop(vk_id, None)
                    bot_logger.info(f"User {vk_id} registered successfully")
                    await message.answer(
                        f"{auth_result['message']}\n\n✅ Регистрация успешна!\n"
                        f"Теперь вы можете пользоваться ботом.\n\n"
                        f"📐 Норма расхода: 10 литров = 100 км",
                        keyboard=main_keyboard # type: ignore
                    )
                else:
                    bot_logger.warning(f"User {vk_id} already exists")
                    await message.answer(
                        "❌ Ошибка: пользователь уже зарегистрирован.\n"
                        "Если это не так, обратитесь к администратору."
                    )
            else:
                user_states.pop(vk_id, None)
                bot_logger.warning(f"Auth failed for user {vk_id}: {auth_result['message']}")
                await message.answer(
                    f"{auth_result['message']}\n\n"
                    "Попробуйте зарегистрироваться снова, отправив 'регистрация'."
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
                monthly_total = await asyncio.to_thread(db.get_monthly_total, vk_id)
                expected_km = monthly_total * 10
                
                bot_logger.info(f"User {vk_id} added {value} liters, total monthly: {monthly_total}")
                await message.answer(
                    f"✅ Заправка {value} л добавлена!\n"
                    f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"📊 **Всего за месяц:** {monthly_total} л\n"
                    f"🎯 **Ожидаемый пробег:** {expected_km} км\n"
                    f"(из расчета 10 л/100 км)",
                    keyboard=main_keyboard # type: ignore
                )
            else:
                await message.answer("❌ Ошибка при добавлении заправки.")
        except ValueError:
            await message.answer("❌ Введите положительное целое число литров.")
    
    else:
        is_registered = await asyncio.to_thread(db.check_user_exists, vk_id)
        if not is_registered:
            user_states[vk_id] = "awaiting_login"
            await message.answer(
                "👋 Для работы зарегистрируйтесь.\n"
                "Введите ваш ЛОГИН от сайта:"
            )
        else:
            await message.answer(
                "Используйте кнопки меню для работы с ботом.\n\n"
                "📐 Норма расхода: 10 литров = 100 км",
                keyboard=main_keyboard # type: ignore
            )

# Запуск
if __name__ == "__main__":
    try:
        if db.check_user_exists(1):
            bot_logger.info("Database connection OK")
            print("✅ Database connection OK")
    except Exception as e:
        bot_logger.error(f"Database connection failed: {e}")
        print(f"❌ Database connection failed: {e}")
        exit(1)
    
    bot_logger.info("Bot started")
    print("🤖 Бот запущен!")
    print("📐 Норма расхода: 10 литров = 100 км")
    print(f"📁 Логи сохраняются в: {os.getenv('LOG_DIR', '.')}")
    print(f"📊 Excel отчеты сохраняются в: excel_reports/")
    
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        bot_logger.info("Bot stopped by user")
        print("\n🛑 Бот остановлен")