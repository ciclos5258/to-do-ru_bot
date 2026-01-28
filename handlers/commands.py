from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import create_main_keyboard

router = Router()
db = Database()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = message.from_user
    db.add_user(message.chat.id, user.username, user.first_name)
    welcome_text = "🎯 Добро пожаловать в To-Do Bot!\n\nИспользуйте меню ниже 👇"
    await message.answer(welcome_text, reply_markup=create_main_keyboard())

@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        return
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=create_main_keyboard())

@router.callback_query(F.data == "cancel_action")
async def cancel_handler_inline(callback: types.CallbackQuery, state: FSMContext):
    if await state.get_state() is not None:
        await state.clear()
        await callback.message.answer("Действие отменено.", reply_markup=create_main_keyboard())
    else:
        await callback.answer("Нет активного действия")
        await callback.message.delete()
    await callback.answer()

@router.message()
async def handle_other_messages(message: types.Message):
    await message.answer("Я не понимаю эту команду. Используйте кнопки из меню.", reply_markup=create_main_keyboard())