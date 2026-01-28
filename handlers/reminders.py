import asyncio
import logging
import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from database import Database
from states import TaskStates
from utils import parse_time
from keyboards import create_main_keyboard, get_cancel_inline_keyboard

router = Router()
db = Database()
logger = logging.getLogger(__name__)

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

async def check_reminders(bot):
    while True:
        try:
            reminders = db.get_due_reminders()
            for reminder in reminders:
                reminder_id, chat_id, name, time_str, is_sent = reminder
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ Напоминание: {name}\nВремя: {time_str}"
                )
                db.mark_reminder_sent(reminder_id)

            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            days_map = {
                0: "monday", 1: "tuesday", 2: "wednesday", 
                3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"
            }
            current_day = days_map[now.weekday()]

            schedule_items = db.get_schedule_for_now(current_day, current_time)
            for user_id, text in schedule_items:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"🗓 **Расписание на сегодня ({current_day}):**\n🔔 {text}"
                )
            
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in check_reminders: {e}")
            await asyncio.sleep(60)