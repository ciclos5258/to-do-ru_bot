import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from handlers import router
from reminders import check_reminders
from database import Database


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


load_dotenv()

async def run_bot():
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    
    
    asyncio.create_task(check_reminders(bot))
    
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Запуск бота (попытка {attempt + 1}/{max_retries})...")
            await dp.start_polling(bot)
            
        except Exception as e:
            logger.error(f"Ошибка в работе бота: {e}")
            current_delay = min(retry_delay * (2 ** attempt), 300)
            logger.info(f"Перезапуск через {current_delay} секунд...")
            await asyncio.sleep(current_delay)
            
            await bot.session.close()
            bot = Bot(token=os.getenv('BOT_TOKEN'))
            dp = Dispatcher(storage=storage)
            dp.include_router(router)
            asyncio.create_task(check_reminders(bot))
            
        else:
            break
            
    else:
        logger.error(f"Бот не смог запуститься после {max_retries} попыток")
    
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


