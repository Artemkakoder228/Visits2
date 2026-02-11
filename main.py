import asyncio
import logging
import database as db
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.registr import register_handlers
# ДОДАЙТЕ ЦІ ІМПОРТИ
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from keyboard import main_menu_for_student

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функція для розсилки
async def send_reminder(bot: Bot):
    # Назва має збігатися з назвою у database.py
    users = db.get_all_student_ids() 
    for user_id in users:
        try:
            await bot.send_message(
                user_id, 
                "Доброго ранку! ☀️ Час відмітити свій статус у системі.",
                reply_markup=main_menu_for_student()
            )
        except Exception as e:
            logging.error(f"Помилка розсилки для {user_id}: {e}")

async def main():
    db.init_db()
    register_handlers(dp)

    # Налаштування планувальника
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    
    scheduler.add_job(
        db.clear_old_visits, 
        trigger='cron', 
        hour=0, 
        minute=0
    )
    # mon-fri = Пн-Пт; hour=8, minute=30
    scheduler.add_job(
        send_reminder, 
        trigger='cron', 
        day_of_week='mon-fri', 
        hour=8, 
        minute=30, 
        args=[bot]
    )
    
    scheduler.start()
    print("Бот запущений, планувальник працює (Пн-Пт 08:30)...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот вимкнений")