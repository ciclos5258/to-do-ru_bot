from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from database import Database
from states import TaskStates
from keyboards import create_main_keyboard, create_tasks_keyboard, get_cancel_inline_keyboard
from utils import format_tasks_list

router = Router()
db = Database()

@router.message(Command("add"))
@router.message(F.text == "➕ Добавить задачу")
async def add_task_command(message: types.Message, state: FSMContext):
    await message.answer("📝 Введите текст новой задачи:", reply_markup=get_cancel_inline_keyboard())
    await state.set_state(TaskStates.waiting_for_task)

@router.message(TaskStates.waiting_for_task)
async def handle_task_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("❌ Текст не может быть пустым!")
        return
    db.add_task(message.chat.id, text)
    await message.answer(f"✅ Задача добавлена: {text}", reply_markup=create_main_keyboard())
    await state.clear()

@router.message(Command("list"))
@router.message(F.text == "📋 Мои задачи")
async def show_tasks_handler(message: types.Message):
    tasks = db.get_tasks(message.chat.id)
    reminders = db.get_user_reminders(message.chat.id)
    if not tasks and not [r for r in reminders if not r[3]]:
        await message.answer("📭 Задач нет!", reply_markup=create_main_keyboard())
        return
    await message.answer(format_tasks_list(tasks, reminders), reply_markup=create_tasks_keyboard(tasks))

@router.callback_query(F.data.startswith('complete_'))
async def complete_task_callback(callback: types.CallbackQuery):
    task_id = int(callback.data.split('_')[1])
    db.mark_task_done(task_id, callback.message.chat.id)
    tasks = db.get_tasks(callback.message.chat.id)
    
    if not tasks:
        await callback.message.edit_text("🎉 Все задачи выполнены!")
    else:
        reminders = db.get_user_reminders(callback.message.chat.id)
        await callback.message.edit_text(format_tasks_list(tasks, reminders), reply_markup=create_tasks_keyboard(tasks))
    await callback.answer("Задача выполнена! ✅")