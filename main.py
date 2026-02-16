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

# Зменшуємо рівень логів для aiogram, щоб не перевантажувати stdout на Render
logging.getLogger("aiogram").setLevel(logging.WARNING)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def send_reminder(bot: Bot):
    """
    Оптимізована розсилка з контролем швидкості.
    Запобігає бану від Telegram та перевантаженню процесора.
    """
    logger.info("Запуск ранкової розсилки...")
    users = await db.get_all_student_ids()
    
    count = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, "Доброго ранку! Час відмітити статус.")
            count += 1
            
            # Пауза після кожного повідомлення для плавності
            await asyncio.sleep(0.1) 
            
            # Кожні 20 повідомлень робимо довшу паузу для розвантаження системи
            if count % 20 == 0:
                await asyncio.sleep(1.0)
                
        except Exception as e:
            logger.error(f"Не вдалося відправити повідомлення {user_id}: {e}")
            
    logger.info(f"Розсилку завершено. Успішно відправлено: {count} повідомлень.")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    
    try:
        # Ініціалізація пулу з'єднань БД (один раз при запуску)
        logger.info("Ініціалізація пулу бази даних...")
        await db.init_db() 

        logger.info("Реєстрація хендлерів...")
        register_handlers(dp)

        # Налаштування планувальника
        scheduler.add_job(db.clear_old_visits, trigger='cron', hour=0, minute=0)
        scheduler.add_job(send_reminder, trigger='cron', day_of_week='mon-fri', hour=8, minute=30, args=[bot])
        
        scheduler.start()
        logger.info("Планувальник запущено.")

        logger.info("Бот виходить в онлайн...")
        
        # Видаляємо старі повідомлення, щоб бот не відповідав на них при перезапуску
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    except Exception as e:
        logger.critical(f"Критична помилка при запуску: {e}")
    finally:
        logger.info("Зупинка планувальника та закриття сесій...")
        if scheduler.running:
            scheduler.shutdown()
        
        # Закриваємо сесію бота
        await bot.session.close()
        
        # Закриваємо пул з'єднань з базою даних, якщо він був створений
        if db.pool:
            await db.pool.close()
            logger.info("Пул бази даних закрито.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинений користувачем.")