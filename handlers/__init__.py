from aiogram import Router
from . import commands, tasks, reminders

def get_handlers_router() -> Router:
    master_router = Router()
    
    master_router.include_router(tasks.router)
    master_router.include_router(reminders.router)
    master_router.include_router(commands.router)
    
    return master_router