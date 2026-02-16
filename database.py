import asyncpg
from datetime import datetime
from config import DATABASE_URL
from aiogram.fsm.state import State, StatesGroup

# Глобальна змінна для пулу з'єднань
pool = None
# Кеш для ролей користувачів (tg_id: role)
role_cache = {}

class AuthState(StatesGroup):
    wait_for_class = State()
    wait_for_email = State()
    wait_for_teacher_code = State()
    wait_for_teacher_email = State()
    wait_for_name = State()
    wait_for_absent_class = State()

async def init_db():
    """Ініціалізація пулу з'єднань та створення таблиць"""
    global pool
    # Створюємо пул (max_size=10 оптимально для безкоштовних тарифів Neon)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                tg_id BIGINT PRIMARY KEY,
                full_name TEXT,
                email TEXT,
                role TEXT,
                class_name TEXT
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS allowed_emails (
                email TEXT PRIMARY KEY,
                class_name TEXT,
                full_name TEXT
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT REFERENCES users(tg_id),
                status TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

async def register_user(tg_id, full_name, email, role, class_name=None):
    """Реєстрація або оновлення даних користувача"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (tg_id, full_name, email, role, class_name)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tg_id) DO UPDATE 
            SET full_name = $2, email = $3, role = $4, class_name = $5
        ''', tg_id, full_name, email, role, class_name)
    
    # Оновлюємо кеш, щоб зміни підтягнулися миттєво
    role_cache[tg_id] = role

async def get_user_role(tg_id):
    """Отримання ролі з кешу або з бази даних"""
    if tg_id in role_cache:
        return role_cache[tg_id]
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT role FROM users WHERE tg_id = $1', tg_id)
        role = row['role'] if row else None
        
        if role:
            role_cache[tg_id] = role
        return role

async def log_visit(tg_id, status):
    """Запис візиту студента"""
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO visits (tg_id, status) VALUES ($1, $2)', tg_id, status)

async def get_allowed_user_data(email):
    """Перевірка наявності email у списку дозволених"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT full_name, class_name FROM allowed_emails WHERE email = $1', 
            email.lower()
        )
        return (row['full_name'], row['class_name']) if row else None

async def get_absent_students(class_name):
    """Отримання списку студентів, які ще не відмітилися сьогодні"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT DISTINCT full_name FROM allowed_emails 
            WHERE class_name = $1 AND email NOT IN (
                SELECT u.email FROM visits v
                JOIN users u ON v.tg_id = u.tg_id 
                WHERE v.timestamp::date = CURRENT_DATE
            )
        ''', class_name)
        return [f"------------------------\n{r['full_name']}❌" for r in rows]

async def get_all_today_visits_raw():
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT u.full_name, v.status, v.timestamp
            FROM visits v
            INNER JOIN users u ON v.tg_id = u.tg_id
            WHERE v.timestamp::date = CURRENT_DATE
            AND v.id IN (SELECT MAX(id) FROM visits WHERE timestamp::date = CURRENT_DATE GROUP BY tg_id)
            ORDER BY v.timestamp DESC
        ''')
        return rows

async def get_all_student_ids():
    """Отримання ID всіх студентів для розсилки"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT tg_id FROM users WHERE role = $1', 'student')
        return [r['tg_id'] for r in rows]

async def clear_old_visits():
    """Видалення записів минулих днів (для планувальника)"""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM visits WHERE timestamp::date < CURRENT_DATE")