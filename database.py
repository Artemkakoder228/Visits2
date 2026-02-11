import sqlite3
from datetime import datetime

# Назва файлу бази даних
DB_NAME = 'visits.db'

def init_db():
    """Ініціалізація бази даних: створення таблиць, якщо вони не існують."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблиця користувачів (id, ПІБ, пошта, роль)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            full_name TEXT,
            email TEXT,
            role TEXT,
            class_name TEXT
        )
    ''')

    # Таблиця дозволених пошт з колонкою full_name
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS allowed_emails (
            email TEXT PRIMARY KEY,
            class_name TEXT,
            full_name TEXT
        )
    ''')
    
    # Таблиця візитів
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            status TEXT,
            timestamp TEXT,
            FOREIGN KEY (tg_id) REFERENCES users (tg_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def register_user(tg_id, full_name, email, role, class_name=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (tg_id, full_name, email, role, class_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (tg_id, full_name, email, role, class_name))
    conn.commit()
    conn.close()

def is_email_in_class(email, class_name):
    """Перевірка, чи належить пошта цьому класу."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM allowed_emails WHERE email = ? AND class_name = ?', (email.lower(), class_name))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_user_role(tg_id):
    """Отримання ролі користувача за його Telegram ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT role FROM users WHERE tg_id = ?', (tg_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def log_visit(tg_id, status):
    """Запис статусу відвідування (Прибув, В дорозі тощо) з часовою міткою."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO visits (tg_id, status, timestamp)
        VALUES (?, ?, ?)
    ''', (tg_id, status, now))
    conn.commit()
    conn.close()

def get_allowed_email_data(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT class_name, full_name FROM allowed_emails WHERE email = ?', (email.lower(),))
    result = cursor.fetchone()
    conn.close()
    return result # Поверне (class_name, full_name) або None

def get_absent_students(class_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Використовуємо DISTINCT, щоб уникнути повторень прізвищ
    cursor.execute('''
        SELECT DISTINCT full_name FROM allowed_emails 
        WHERE class_name = ? AND email NOT IN (
            SELECT users.email FROM visits 
            JOIN users ON visits.tg_id = users.tg_id 
            WHERE visits.timestamp LIKE ?
        )
    ''', (class_name, f'{today}%'))
    
    absent = cursor.fetchall()
    conn.close()
    
    # Якщо список порожній, повертаємо порожній список
    if not absent:
        return []

    # Формуємо список із вашим оформленням
    formatted_list = []
    separator = "------------------------"
    
    for row in absent:
        formatted_list.append(separator)
        formatted_list.append(f"{row[0]}❌")
    
    return formatted_list

def get_all_students():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Вибираємо тільки тих, хто зареєстрований як учень
    cursor.execute('SELECT tg_id FROM users WHERE role = "student"')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_all_student_ids():
    """Повертає список Telegram ID всіх користувачів з роллю student."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT tg_id FROM users WHERE role = "student"')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_allowed_user_data(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT full_name, class_name FROM allowed_emails WHERE email = ?', (email.lower(),))
    result = cursor.fetchone()
    conn.close()
    return result

def clear_old_visits():
    """Видаляє всі записи про візити за попередні дні, залишаючи лише сьогоднішні."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    # Видалити все, що не починається з сьогоднішньої дати
    cursor.execute("DELETE FROM visits WHERE timestamp NOT LIKE ?", (f'{today}%',))
    conn.commit()
    conn.close()

def get_all_today_visits():
    """Отримання списку всіх відміток за сьогодні для вчителя."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Об'єднуємо таблиці, щоб отримати ПІБ користувача разом зі статусом
    cursor.execute('''
        SELECT users.full_name, visits.status, visits.timestamp
        FROM visits
        JOIN users ON visits.tg_id = users.tg_id
        WHERE visits.timestamp LIKE ?
        ORDER BY visits.timestamp DESC
    ''', (f'{today}%',))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "Сьогодні ще ніхто не відмічався."
    
    # Форматуємо список у зручний текст
    report = ""
    for name, status, time in rows:
        report += f"📍 {name}: {status} ({time.split()[1]})\n"
    return report