import logging
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
import asyncio
import time
from datetime import datetime, timedelta
import re

# Импортируем нашу базу данных
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Создаем роутер
router = Router()

# Создаем состояния
class TaskStates(StatesGroup):
    waiting_for_task = State()
    waiting_for_reminder_name = State()
    waiting_for_reminder_time = State()

# Создаем клавиатуру
def create_main_keyboard():
    """Создает основную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="➕ Добавить задачу")],
        [KeyboardButton(text="⏰ Добавить напоминание"), KeyboardButton(text="✅ Выполненные")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Функция для создания клавиатуры с задачами
def create_tasks_keyboard(tasks):
    """Создает inline-клавиатуру с задачами"""
    keyboard = []
    for task in tasks:
        task_id, text, is_done = task
        if not is_done:  # Только для невыполненных задач
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ Выполнить: {text[:15]}...", 
                    callback_data=f"complete_{task_id}"
                )
            ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

# Функция для парсинга времени
def parse_time(time_str):
    """Парсит время из строки в формате ЧЧ:ММ или ЧЧ.ММ"""
    try:
        # Заменяем точку на двоеточие для унификации
        time_str = time_str.replace('.', ':')
        
        # Проверяем формат времени
        time_pattern = r'^(\d{1,2})[:.](\d{2})$'
        match = re.match(time_pattern, time_str)
        
        if not match:
            return None
            
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            return None
            
        return hours, minutes
        
    except (ValueError, AttributeError):
        return None

# Функция для расчета оставшегося времени до напоминания
def get_time_until_reminder(reminder_time):
    """Рассчитывает оставшееся время до напоминания"""
    now = datetime.now()
    reminder_hour, reminder_minute = map(int, reminder_time.split(':'))
    
    # Создаем объект времени напоминания на сегодня
    reminder_today = now.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)
    
    # Если время уже прошло сегодня, планируем на завтра
    if reminder_today < now:
        reminder_today += timedelta(days=1)
    
    time_left = reminder_today - now
    hours_left = time_left.seconds // 3600
    minutes_left = (time_left.seconds % 3600) // 60
    
    if hours_left > 0:
        return f"{hours_left}ч {minutes_left}м"
    else:
        return f"{minutes_left}м"

# Функция для отправки напоминаний
async def check_reminders(bot: Bot):
    """Проверяет и отправляет напоминания"""
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M")
            reminders = db.get_due_reminders(current_time)
            
            for reminder in reminders:
                reminder_id, chat_id, name, time_str = reminder
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ **Напоминание**: {name}\nВремя: {time_str}",
                    parse_mode="Markdown"
                )
                db.mark_reminder_sent(reminder_id)
                
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            
        except Exception as e:
            logger.error(f"Ошибка в проверке напоминаний: {e}")
            await asyncio.sleep(60)

# Обработчики команд
@router.message(Command("start"))
async def start(message: types.Message):
    """Обработчик команды /start"""
    user = message.from_user
    chat_id = message.chat.id
    
    # Добавляем пользователя в базу
    db.add_user(chat_id, user.username, user.first_name)
    
    # Приветственное сообщение
    welcome_text = """
    🎯 Добро пожаловать в To-Do Bot!

    Вот что я умею:
    /add - Добавить новую задачу
    /list - Показать текущие задачи и напоминания
    /done <ID> - Отметить задачу выполненной
    /delete <ID> - Удалить задачу
    /reminders - Показать мои напоминания

    Или используйте кнопки ниже 👇
    """
    
    await message.answer(welcome_text, reply_markup=create_main_keyboard())

@router.message(Command("reminders"))
async def show_reminders(message: types.Message):
    """Показывает все напоминания пользователя"""
    chat_id = message.chat.id
    reminders = db.get_user_reminders(chat_id)
    
    if not reminders:
        await message.answer(
            "📭 У вас нет активных напоминаний!",
            reply_markup=create_main_keyboard()
        )
        return
    
    reminders_text = "⏰ Ваши напоминания:\n\n"
    for i, reminder in enumerate(reminders, 1):
        reminder_id, name, time_str, is_sent = reminder
        status = "✅ Отправлено" if is_sent else "⏰ Ожидает"
        
        if not is_sent:
            time_left = get_time_until_reminder(time_str)
            status = f"⏰ Через {time_left}"
            
        reminders_text += f"{i}. {name} - {time_str} ({status})\n"
    
    await message.answer(reminders_text, reply_markup=create_main_keyboard())

@router.message(F.text == "⏰ Добавить напоминание")
async def add_reminder_command(message: types.Message, state: FSMContext):
    """Обработчик кнопки добавления напоминания"""
    await message.answer(
        "📝 Введите название напоминания:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TaskStates.waiting_for_reminder_name)

@router.message(TaskStates.waiting_for_reminder_name)
async def handle_reminder_name(message: types.Message, state: FSMContext):
    """Обрабатывает ввод названия напоминания"""
    name = message.text.strip()
    
    if not name:
        await message.answer("❌ Название не может быть пустым!")
        return
    
    await state.update_data(reminder_name=name)
    await message.answer(
        "⏰ Введите время напоминания в формате ЧЧ:ММ (например, 14:30 или 9.05):"
    )
    await state.set_state(TaskStates.waiting_for_reminder_time)

@router.message(TaskStates.waiting_for_reminder_time)
async def handle_reminder_time(message: types.Message, state: FSMContext):
    """Обрабатывает ввод времени напоминания"""
    time_str = message.text.strip()
    chat_id = message.chat.id
    
    # Парсим время
    time_data = parse_time(time_str)
    if not time_data:
        await message.answer(
            "❌ Неверный формат времени! Используйте ЧЧ:ММ (например, 14:30 или 9.05)"
        )
        return
    
    hours, minutes = time_data
    formatted_time = f"{hours:02d}:{minutes:02d}"
    
    # Получаем название из состояния
    data = await state.get_data()
    name = data.get('reminder_name', 'Без названия')
    
    # Добавляем напоминание в базу
    success = db.add_reminder(chat_id, name, formatted_time)
    
    if success:
        time_left = get_time_until_reminder(formatted_time)
        await message.answer(
            f"⏰ Напоминание добавлено!\nНазвание: {name}\nВремя: {formatted_time}\nНапомню через: {time_left}",
            reply_markup=create_main_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при добавлении напоминания. Попробуйте еще раз.",
            reply_markup=create_main_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data.startswith('complete_'))
async def button_click(callback: types.CallbackQuery):
    """Обрабатывает нажатия на inline-кнопки"""
    chat_id = callback.message.chat.id
    data = callback.data
    
    # Обрабатываем нажатие
    if data.startswith('complete_'):
        # Извлекаем ID задачи из callback_data
        task_id = int(data.split('_')[1])
        
        # Отмечаем задачу как выполненную
        success = db.mark_task_done(task_id, chat_id)
        
        if success:
            # Получаем обновленный список задач
            tasks = db.get_tasks(chat_id)
            
            if not tasks:
                # Если задач больше нет, показываем сообщение
                await callback.message.edit_text(
                    text="🎉 Все задачи выполнены! Добавьте новые задачи.",
                    reply_markup=None
                )
            else:
                # Формируем обновленный текст с задачами
                tasks_text = "📋 Ваши активные задачи:\n\n"
                for i, task in enumerate(tasks, 1):
                    task_id, text, is_done = task
                    status = "✅" if is_done else "⏳"
                    tasks_text += f"{i}. {status} {text}\nID: {task_id}\n\n"
                
                # Создаем обновленную клавиатуру
                reply_markup = create_tasks_keyboard(tasks)
                
                # Обновляем сообщение с новыми данными
                await callback.message.edit_text(
                    text=tasks_text,
                    reply_markup=reply_markup
                )
            
            await callback.answer("Задача выполнена! ✅")
        else:
            await callback.answer("❌ Ошибка: задача не найдена")

@router.message(Command("list"))
@router.message(F.text == "📋 Мои задачи")
async def show_tasks(message: types.Message):
    """Показывает текущие задачи и напоминания с кнопками для выполнения"""
    chat_id = message.chat.id
    
    # Получаем задачи
    tasks = db.get_tasks(chat_id)
    
    # Получаем напоминания
    reminders = db.get_user_reminders(chat_id)
    active_reminders = [r for r in reminders if not r[3]]  # Только неотправленные
    
    if not tasks and not active_reminders:
        await message.answer(
            "📭 У вас нет активных задач и напоминаний!",
            reply_markup=create_main_keyboard()
        )
        return
    
    # Формируем текст с задачами и напоминаниями
    tasks_text = "📋 Ваши активные задачи и напоминания:\n\n"
    
    # Добавляем задачи
    if tasks:
        tasks_text += "📝 **Задачи:**\n"
        for i, task in enumerate(tasks, 1):
            task_id, text, is_done = task
            status = "✅" if is_done else "⏳"
            tasks_text += f"{i}. {status} {text}\nID: {task_id}\n\n"
    
    # Добавляем напоминания с таймерами
    if active_reminders:
        tasks_text += "⏰ **Напоминания:**\n"
        for i, reminder in enumerate(active_reminders, 1):
            reminder_id, name, time_str, is_sent = reminder
            time_left = get_time_until_reminder(time_str)
            tasks_text += f"{i + len(tasks) if tasks else i}. ⏰ {name} - {time_str} (через {time_left})\nID: R{reminder_id}\n\n"
    
    # Создаем клавиатуру только для задач (не для напоминаний)
    reply_markup = create_tasks_keyboard(tasks)
    
    # Отправляем сообщение с кнопками
    await message.answer(
        tasks_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

@router.message(Command("add"))
@router.message(F.text == "➕ Добавить задачу")
async def add_task_command(message: types.Message, state: FSMContext):
    """Обработчик команды /add"""
    await message.answer(
        "📝 Введите текст новой задачи:",
        reply_markup=ReplyKeyboardRemove()
    )
    # Устанавливаем состояние ожидания текста задачи
    await state.set_state(TaskStates.waiting_for_task)

@router.message(TaskStates.waiting_for_task)
async def handle_task_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод текста задачи"""
    chat_id = message.chat.id
    text = message.text.strip()
    
    if not text:
        await message.answer("❌ Текст задачи не может быть пустым!")
        return
    
    # Убедимся, что пользователь существует в базе
    user = message.from_user
    db.add_user(chat_id, user.username, user.first_name)
    
    # Добавляем задачу в базу
    success = db.add_task(chat_id, text)
    
    if success:
        await message.answer(
            f"✅ Задача добавлена: {text}",
            reply_markup=create_main_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при добавлении задачи. Попробуйте еще раз.",
            reply_markup=create_main_keyboard()
        )
    
    # Сбрасываем состояние
    await state.clear()

@router.message(Command("done"))
async def mark_done(message: types.Message, command: CommandObject):
    """Отмечает задачу как выполненную"""
    if not command.args:
        await message.answer("❌ Используйте: /done <ID_задачи>")
        return
    
    try:
        task_id = int(command.args.strip())
        chat_id = message.chat.id
        
        success = db.mark_task_done(task_id, chat_id)
        
        if success:
            # После выполнения задачи показываем обновленный список
            tasks = db.get_tasks(chat_id)
            reminders = db.get_user_reminders(chat_id)
            active_reminders = [r for r in reminders if not r[3]]
            
            if not tasks and not active_reminders:
                await message.answer(
                    "🎉 Все задачи выполнены! Добавьте новые задачи.",
                    reply_markup=create_main_keyboard()
                )
            else:
                tasks_text = "📋 Ваши активные задачи и напоминания:\n\n"
                
                if tasks:
                    tasks_text += "📝 **Задачи:**\n"
                    for i, task in enumerate(tasks, 1):
                        task_id, text, is_done = task
                        status = "✅" if is_done else "⏳"
                        tasks_text += f"{i}. {status} {text}\nID: {task_id}\n\n"
                
                if active_reminders:
                    tasks_text += "⏰ **Напоминания:**\n"
                    for i, reminder in enumerate(active_reminders, 1 if tasks else 1):
                        reminder_id, name, time_str, is_sent = reminder
                        time_left = get_time_until_reminder(time_str)
                        tasks_text += f"{i + len(tasks) if tasks else i}. ⏰ {name} - {time_str} (через {time_left})\nID: R{reminder_id}\n\n"
                
                reply_markup = create_tasks_keyboard(tasks)
                await message.answer(tasks_text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await message.answer("❌ Задача не найдена!")
            
    except ValueError:
        await message.answer("❌ ID задачи должен быть числом!")

@router.message(Command("delete"))
async def delete_task(message: types.Message, command: CommandObject):
    """Удаляет задачу"""
    if not command.args:
        await message.answer("❌ Используйте: /delete <ID_задачи>")
        return
    
    try:
        task_id = int(command.args.strip())
        chat_id = message.chat.id
        
        success = db.delete_task(task_id, chat_id)
        
        if success:
            # После удаления задачи показываем обновленный список
            tasks = db.get_tasks(chat_id)
            reminders = db.get_user_reminders(chat_id)
            active_reminders = [r for r in reminders if not r[3]]
            
            if not tasks and not active_reminders:
                await message.answer(
                    "📭 Задача удалена! У вас больше нет активных задач и напоминаний.",
                    reply_markup=create_main_keyboard()
                )
            else:
                tasks_text = "📋 Ваши активные задачи и напоминания:\n\n"
                
                if tasks:
                    tasks_text += "📝 **Задачи:**\n"
                    for i, task in enumerate(tasks, 1):
                        task_id, text, is_done = task
                        status = "✅" if is_done else "⏳"
                        tasks_text += f"{i}. {status} {text}\nID: {task_id}\n\n"
                
                if active_reminders:
                    tasks_text += "⏰ **Напоминания:**\n"
                    for i, reminder in enumerate(active_reminders, 1 if tasks else 1):
                        reminder_id, name, time_str, is_sent = reminder
                        time_left = get_time_until_reminder(time_str)
                        tasks_text += f"{i + len(tasks) if tasks else i}. ⏰ {name} - {time_str} (через {time_left})\nID: R{reminder_id}\n\n"
                
                reply_markup = create_tasks_keyboard(tasks)
                await message.answer(
                    f"🗑️ Задача удалена!\n\n{tasks_text}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        else:
            await message.answer("❌ Задача не найдена!")
            
    except ValueError:
        await message.answer("❌ ID задачи должен быть числом!")

@router.message(F.text == "✅ Выполненные")
async def show_completed(message: types.Message):
    """Показывает выполненные задачи"""
    chat_id = message.chat.id
    tasks = db.get_tasks(chat_id, show_done=True)
    
    # Фильтруем только выполненные задачи
    completed_tasks = [task for task in tasks if task[2]]
    
    if not completed_tasks:
        await message.answer(
            "📭 У вас нет выполненных задач!",
            reply_markup=create_main_keyboard()
        )
        return
    
    tasks_text = "✅ Выполненные задачи:\n\n"
    for i, task in enumerate(completed_tasks, 1):
        task_id, text, is_done = task
        tasks_text += f"{i}. ✅ {text}\nID: {task_id}\n\n"
    
    await message.answer(tasks_text, reply_markup=create_main_keyboard())

@router.message()
async def handle_other_messages(message: types.Message):
    """Обрабатывает все остальные сообщения"""
    await message.answer(
        "Я не понимаю эту команду. Используйте кнопки или команды из меню.",
        reply_markup=create_main_keyboard()
    )

async def run_bot():
    """Запускает бота с автоматическим перезапуском при ошибках"""
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    
    # Запускаем проверку напоминаний в фоновом режиме
    asyncio.create_task(check_reminders(bot))
    
    max_retries = 10  # Максимальное количество попыток перезапуска
    retry_delay = 5   # Начальная задержка между попытками в секундах
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Запуск бота (попытка {attempt + 1}/{max_retries})...")
            await dp.start_polling(bot)
            
        except Exception as e:
            logger.error(f"Ошибка в работе бота: {e}")
            
            # Увеличиваем задержку с каждой попыткой (экспоненциальная backoff стратегия)
            current_delay = min(retry_delay * (2 ** attempt), 300)  # Максимум 5 минут
            
            logger.info(f"Перезапуск через {current_delay} секунд...")
            await asyncio.sleep(current_delay)
            
            # Пересоздаем объекты бота и диспетчера
            await bot.session.close()
            bot = Bot(token=os.getenv('BOT_TOKEN'))
            dp = Dispatcher(storage=storage)
            dp.include_router(router)
            
            # Перезапускаем проверку напоминаний
            asyncio.create_task(check_reminders(bot))
            
        else:
            # Если бот остановлен корректно (не из-за ошибки)
            break
            
    else:
        logger.error(f"Бот не смог запуститься после {max_retries} попыток")
    
    # Закрываем сессию при окончательной остановке
    await bot.session.close()

async def main():
    """Основная функция запуска бота"""
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    
    try:
        await run_bot()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        logger.info("Работа бота завершена")

if __name__ == "__main__":
    asyncio.run(main())