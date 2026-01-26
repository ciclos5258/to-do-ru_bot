from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardRemove, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)

def create_main_keyboard():
    keyboard = [
        [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="➕ Добавить задачу")],
        [KeyboardButton(text="⏰ Добавить напоминание")], [KeyboardButton(text="📜 Расписание")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_tasks_keyboard(tasks):   
    keyboard = []
    for task in tasks:
        task_id, text, is_done = task
        if not is_done:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ {text[:25]}..", 
                    callback_data=f"complete_{task_id}"
                )
            ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

def get_cancel_inline_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def schedule_inline_keyboard():
    keyboard = [
            [InlineKeyboardButton(text="Пн", callback_data="Mon_add"), InlineKeyboardButton(text="Вт", callback_data="Tue_add"), InlineKeyboardButton(text="Ср", callback_data="Wed_add")],
            [InlineKeyboardButton(text="Чт", callback_data="Thu_add"), InlineKeyboardButton(text="Пт", callback_data="Fri_add")]
        ]
