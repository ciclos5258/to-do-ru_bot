from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database import Database
from states import TaskStates
from utils import parse_time, get_time_until_reminder
from keyboards import create_main_keyboard, get_cancel_inline_keyboard

router = Router()
db = Database()

@router.message(F.text == "⏰ Добавить напоминание")
async def add_reminder_command(message: types.Message, state: FSMContext):
    await message.answer("📝 Введите название напоминания:", reply_markup=get_cancel_inline_keyboard())
    await state.set_state(TaskStates.waiting_for_reminder_name)

@router.message(TaskStates.waiting_for_reminder_name)
async def handle_reminder_name(message: types.Message, state: FSMContext):
    await state.update_data(reminder_name=message.text.strip())
    await message.answer("⏰ Введите время (ЧЧ:ММ):")
    await state.set_state(TaskStates.waiting_for_reminder_time)

@router.message(TaskStates.waiting_for_reminder_time)
async def handle_reminder_time(message: types.Message, state: FSMContext):
    time_data = parse_time(message.text.strip())
    if not time_data:
        await message.answer("❌ Неверный формат!")
        return
    
    data = await state.get_data()
    formatted_time = f"{time_data[0]:02d}:{time_data[1]:02d}"
    db.add_reminder(message.chat.id, data['reminder_name'], formatted_time)
    
    await message.answer(f"⏰ Напоминание '{data['reminder_name']}' установлено на {formatted_time}", reply_markup=create_main_keyboard())
    await state.clear()

@router.message(Command("schedule"))
@router.message(F.text == "📜 Расписание")
async def schedule_command(message: types.Message):
    
    await message.answer("📅 Раздел расписания в разработке...")