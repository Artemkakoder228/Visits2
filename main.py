import asyncio
import logging
import sys
import database as db
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.registr import register_handlers
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def send_reminder(bot: Bot):
    logger.info("Запуск ранкової розсилки...")
    users = await db.get_all_student_ids()
    for user_id in users:
        try:
            await bot.send_message(user_id, "Доброго ранку! Час відмітити статус.")
            await asyncio.sleep(0.05) 
        except Exception as e:
            logger.error(f"Не вдалося відправити повідомлення {user_id}: {e}")

async def main():
    try:
        logger.info("Ініціалізація бази даних...")
        await db.init_db() 

        logger.info("Реєстрація хендлерів...")
        register_handlers(dp)

        scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
        scheduler.add_job(db.clear_old_visits, trigger='cron', hour=0, minute=0)
        scheduler.add_job(send_reminder, trigger='cron', day_of_week='mon-fri', hour=8, minute=30, args=[bot])
        
        scheduler.start()
        logger.info("Планувальник запущено.")

        logger.info("Бот виходить в онлайн...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    except Exception as e:
        logger.critical(f"Критична помилка при запуску: {e}")
    finally:
        logger.info("Закриття сесії бота...")
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинений користувачем.")