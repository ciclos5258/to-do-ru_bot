from aiogram import types, Router, F
from aiogram.filters import Command
from keyboards import schedule_inline_keyboard
from states import ScheduleState
from aiogram.fsm.context import FSMContext
from database import Database
from utils import parse_time

router = Router()
db = Database()

@router.message(Command("schedule"))
@router.message(F.text == "📜 Расписание")
async def schedule_command(message: types.Message):
    await message.answer("Выберите день недели", reply_markup=schedule_inline_keyboard())

@router.callback_query(F.data.endswith("_add"))
async def process_day(callback: types.CallbackQuery, state: FSMContext):
    day = callback.data.replace("_add", "")
    await state.update_data(day=day)
    await callback.answer()
    await callback.message.answer("Введите время (например 15:30)")
    await state.set_state(ScheduleState.time)

@router.message(ScheduleState.time)
async def process_time(message: types.Message, state: FSMContext):
    time_data = parse_time(message.text.strip())
    
    if not time_data:
        await message.answer("❌ Неверный формат! Используйте ЧЧ:ММ (например, 08:30 или 15:00)")
        return
    
    formatted_time = f"{time_data[0]:02d}:{time_data[1]:02d}"
    
    await state.update_data(time=formatted_time)
    await message.answer("Введите текст напоминания:")
    await state.set_state(ScheduleState.text)

@router.message(ScheduleState.text)
async def process_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    day = data["day"]
    time = data["time"]
    text = message.text

    db.add_schedule_item(user_id, day, time, text)

    await message.answer("Расписание сохранено 🗓️")
    await state.clear()
