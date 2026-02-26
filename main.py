import asyncio
import logging
import sys
import database as db
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.registr import register_handlers
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logging.getLogger("aiogram").setLevel(logging.WARNING)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def send_reminder(bot: Bot):
    """Оптимізована розсилка сповіщень учням"""
    logger.info("Запуск розсилки сповіщень...")
    users = await db.get_all_student_ids() #
    
    count = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, "Доброго ранку! Не забудьте відмітити свій статус.")
            count += 1
            await asyncio.sleep(0.1) # Пауза для уникнення лімітів Telegram
            
            if count % 20 == 0:
                await asyncio.sleep(1.0)
                
        except Exception as e:
            logger.error(f"Не вдалося відправити повідомлення {user_id}: {e}")
            
    logger.info(f"Розсилку завершено. Успішно відправлено: {count} повідомлень.")

async def main():
    # Використовуємо Київську таймзону для планувальника
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    
    try:
        logger.info("Ініціалізація пулу бази даних...")
        await db.init_db() #

        logger.info("Реєстрація хендлерів...")
        register_handlers(dp) #

        # --- НАЛАШТУВАННЯ ПЛАНУВАЛЬНИКА ---
        
        # 1. Очищення старих візитів о 03:00 ранку
        scheduler.add_job(db.clear_old_visits, trigger='cron', hour=3, minute=0)
        
        # 2. Перше сповіщення о 08:20
        scheduler.add_job(send_reminder, trigger='cron', day_of_week='mon-fri', hour=8, minute=20, args=[bot])
        
        # 3. Друге сповіщення о 08:30
        scheduler.add_job(send_reminder, trigger='cron', day_of_week='mon-fri', hour=8, minute=30, args=[bot])
        
        scheduler.start()
        logger.info("Планувальник запустив завдання (03:00 - очищення, 08:20 та 08:30 - сповіщення).")

        logger.info("Бот онлайн...")
        
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    except Exception as e:
        logger.critical(f"Критична помилка при запуску: {e}")
    finally:
        logger.info("Зупинка планувальника та закриття сесій...")
        if scheduler.running:
            scheduler.shutdown()
        await bot.session.close()
        if db.pool:
            await db.pool.close()
            logger.info("Пул бази даних закрито.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинений.")