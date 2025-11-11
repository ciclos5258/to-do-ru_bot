from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from database import Database
from states import TaskStates
from keyboards import create_main_keyboard, create_tasks_keyboard
from utils import parse_time, get_time_until_reminder, format_tasks_list

router = Router()
db = Database()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = message.from_user
    chat_id = message.chat.id
    
    db.add_user(chat_id, user.username, user.first_name)
    
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

@router.message(Command("add"))
@router.message(F.text == "➕ Добавить задачу")
async def add_task_command(message: types.Message, state: FSMContext):
    await message.answer("📝 Введите текст новой задачи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(TaskStates.waiting_for_task)

@router.message(TaskStates.waiting_for_task)
async def handle_task_input(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    text = message.text.strip()
    
    if not text:
        await message.answer("❌ Текст задачи не может быть пустым!")
        return
    
    user = message.from_user
    db.add_user(chat_id, user.username, user.first_name)
    
    success = db.add_task(chat_id, text)
    
    if success:
        await message.answer(f"✅ Задача добавлена: {text}", reply_markup=create_main_keyboard())
    else:
        await message.answer("❌ Ошибка при добавлении задачи. Попробуйте еще раз.", reply_markup=create_main_keyboard())
    
    await state.clear()

@router.message(Command("list"))
@router.message(F.text == "📋 Мои задачи")
async def show_tasks_handler(message: types.Message):
    chat_id = message.chat.id
    
    tasks = db.get_tasks(chat_id)
    reminders = db.get_user_reminders(chat_id)
    active_reminders = [r for r in reminders if not r[3]]
    
    if not tasks and not active_reminders:
        await message.answer("📭 У вас нет активных задач и напоминаний!", reply_markup=create_main_keyboard())
        return
    
    tasks_text = format_tasks_list(tasks, reminders)
    reply_markup = create_tasks_keyboard(tasks)
    
    await message.answer(tasks_text, reply_markup=reply_markup)

@router.message(Command("done"))
async def mark_done_handler(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer("❌ Используйте: /done <ID_задачи>")
        return
    
    try:
        task_id = int(command.args.strip())
        chat_id = message.chat.id
        
        success = db.mark_task_done(task_id, chat_id)
        
        if success:
            await show_updated_task_list(message, chat_id, "Задача выполнена! ✅")
        else:
            await message.answer("❌ Задача не найдена!")
            
    except ValueError:
        await message.answer("❌ ID задачи должен быть числом!")

@router.message(Command("delete"))
async def delete_task_handler(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer("❌ Используйте: /delete <ID_задачи>")
        return
    
    try:
        task_id = int(command.args.strip())
        chat_id = message.chat.id
        
        success = db.delete_task(task_id, chat_id)
        
        if success:
            await show_updated_task_list(message, chat_id, "🗑️ Задача удалена!")
        else:
            await message.answer("❌ Задача не найдена!")
            
    except ValueError:
        await message.answer("❌ ID задачи должен быть числом!")

@router.message(F.text == "✅ Выполненные")
async def show_completed_handler(message: types.Message):
    chat_id = message.chat.id
    tasks = db.get_tasks(chat_id, show_done=True)
    
    completed_tasks = [task for task in tasks if task[2]]
    
    if not completed_tasks:
        await message.answer("📭 У вас нет выполненных задач!", reply_markup=create_main_keyboard())
        return
    
    tasks_text = "✅ Выполненные задачи:\n\n"
    for i, task in enumerate(completed_tasks, 1):
        task_id, text, is_done = task
        tasks_text += f"{i}. ✅ {text}\nID: {task_id}\n\n"
    
    await message.answer(tasks_text, reply_markup=create_main_keyboard())

@router.message(Command("reminders"))
async def show_reminders_handler(message: types.Message):
    chat_id = message.chat.id
    reminders = db.get_user_reminders(chat_id)
    
    if not reminders:
        await message.answer("📭 У вас нет активных напоминаний!", reply_markup=create_main_keyboard())
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
    await message.answer("📝 Введите название напоминания:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(TaskStates.waiting_for_reminder_name)

@router.message(TaskStates.waiting_for_reminder_name)
async def handle_reminder_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    
    if not name:
        await message.answer("❌ Название не может быть пустым!")
        return
    
    await state.update_data(reminder_name=name)
    await message.answer("⏰ Введите время напоминания в формате ЧЧ:ММ (например, 14:30 или 9.05):")
    await state.set_state(TaskStates.waiting_for_reminder_time)

@router.message(TaskStates.waiting_for_reminder_time)
async def handle_reminder_time(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    chat_id = message.chat.id
    
    time_data = parse_time(time_str)
    if not time_data:
        await message.answer("❌ Неверный формат времени! Используйте ЧЧ:ММ (например, 14:30 или 9.05)")
        return
    
    hours, minutes = time_data
    formatted_time = f"{hours:02d}:{minutes:02d}"
    
    data = await state.get_data()
    name = data.get('reminder_name', 'Без названия')
    
    success = db.add_reminder(chat_id, name, formatted_time)
    
    if success:
        time_left = get_time_until_reminder(formatted_time)
        await message.answer(f"⏰ Напоминание добавлено!\nНазвание: {name}\nВремя: {formatted_time}\nНапомню через: {time_left}", reply_markup=create_main_keyboard())
    else:
        await message.answer("❌ Ошибка при добавлении напоминания. Попробуйте еще раз.", reply_markup=create_main_keyboard())
    
    await state.clear()

@router.callback_query(F.data.startswith('complete_'))
async def complete_task_callback(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    task_id = int(callback.data.split('_')[1])
    
    success = db.mark_task_done(task_id, chat_id)
    
    if success:
        tasks = db.get_tasks(chat_id)
        
        if not tasks:
            await callback.message.edit_text(text="🎉 Все задачи выполнены! Добавьте новые задачи.", reply_markup=None)
        else:
            reminders = db.get_user_reminders(chat_id)
            tasks_text = format_tasks_list(tasks, reminders)
            reply_markup = create_tasks_keyboard(tasks)
            
            await callback.message.edit_text(text=tasks_text, reply_markup=reply_markup)
        
        await callback.answer("Задача выполнена! ✅")
    else:
        await callback.answer("❌ Ошибка: задача не найдена")

async def show_updated_task_list(message: types.Message, chat_id: int, prefix_text: str = ""):
    tasks = db.get_tasks(chat_id)
    reminders = db.get_user_reminders(chat_id)
    active_reminders = [r for r in reminders if not r[3]]
    
    if not tasks and not active_reminders:
        await message.answer(f"{prefix_text}\n\n🎉 Все задачи выполнены! Добавьте новые задачи.", reply_markup=create_main_keyboard())
        return
    
    tasks_text = format_tasks_list(tasks, reminders)
    reply_markup = create_tasks_keyboard(tasks)
    
    full_text = f"{prefix_text}\n\n{tasks_text}" if prefix_text else tasks_text
    
    await message.answer(full_text, reply_markup=reply_markup)

@router.message()
async def handle_other_messages(message: types.Message):
    await message.answer("Я не понимаю эту команду. Используйте кнопки или команды из меню.", reply_markup=create_main_keyboard())