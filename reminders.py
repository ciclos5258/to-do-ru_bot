import asyncio
import logging
from database import Database

logger = logging.getLogger(__name__)
db = Database()

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
                print(f"Отправлено напоминание: {name} пользователю {chat_id}")
                
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Ошибка в проверке напоминаний: {e}")
            await asyncio.sleep(60)