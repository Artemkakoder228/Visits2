import asyncio
import database as db
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.registr import register_handlers
from apscheduler.schedulers.asyncio import AsyncIOScheduler

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def send_reminder(bot: Bot):
    users = await db.get_all_student_ids() # Додано await
    for user_id in users:
        try:
            await bot.send_message(user_id, "Доброго ранку! Час відмітити статус.")
        except Exception:
            pass

async def main():
    await db.init_db() # Асинхронна ініціалізація
    register_handlers(dp)

    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(db.clear_old_visits, trigger='cron', hour=0, minute=0)
    scheduler.add_job(send_reminder, trigger='cron', day_of_week='mon-fri', hour=8, minute=30, args=[bot])
    
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())