from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import TEACHER_SECRET_CODE
from keyboard import class_selection_menu, regestration, main_menu_for_teacher, main_menu_for_student
import database as db 

router = Router()

# Визначаємо стани для FSM
class AuthState(StatesGroup):
    wait_for_class = State()        # Вибір класу для учня
    wait_for_email = State()        # Введення пошти для учня
    wait_for_teacher_code = State() # Введення коду для вчителя
    wait_for_teacher_email = State()# Введення пошти для вчителя (підтягування ПІБ)
    wait_for_name = State()         # Введення ПІБ (якщо немає в базі)
    wait_for_absent_class = State()  # Вибір класу для перевірки відсутніх

# --- Головне меню та вхід ---

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user_role = db.get_user_role(message.from_user.id)
    
    if user_role == "teacher":
        await message.answer("Вітаю, вчителю!", reply_markup=main_menu_for_teacher())
    elif user_role == "student":
        await message.answer("Привіт! Оберіть статус:", reply_markup=main_menu_for_student())
    else:
        await message.answer(
            "Вітаємо у системі Visits! Оберіть варіант входу:", 
            reply_markup=regestration()
        )

# --- Логіка Учня (Навігація: Клас -> Пошта -> ПІБ) ---

@router.message(F.text == "Учень: Реєстрація за email")
async def student_reg_start(message: Message, state: FSMContext):
    await state.clear() 
    await message.answer("Оберіть ваш клас:", reply_markup=class_selection_menu())
    await state.set_state(AuthState.wait_for_class)

@router.message(AuthState.wait_for_class, F.text == "⬅️ Назад")
async def back_from_class(message: Message, state: FSMContext):
    await state.clear()
    await cmd_start(message)

@router.message(AuthState.wait_for_class)
async def process_class_selection(message: Message, state: FSMContext):
    selected_class = message.text
    await state.update_data(class_name=selected_class)
    await message.answer(
        f"Ви обрали клас: {selected_class}.\nТепер введіть вашу пошту:",
        reply_markup=class_selection_menu() 
    )
    await state.set_state(AuthState.wait_for_email)

@router.message(AuthState.wait_for_email, F.text == "⬅️ Назад")
async def back_from_email(message: Message, state: FSMContext):
    await message.answer("Оберіть ваш клас заново:", reply_markup=class_selection_menu())
    await state.set_state(AuthState.wait_for_class)

@router.message(AuthState.wait_for_email)
async def process_email(message: Message, state: FSMContext):
    email = message.text.lower()
    data = await state.get_data()
    class_name = data.get('class_name')
    
    # Перевіряємо в дозволених списках
    user_data = db.get_allowed_user_data(email)
    
    if user_data and user_data[1] == class_name:
        full_name = user_data[0]
        # Автоматична реєстрація учня, якщо ім'я вже є в allowed_emails
        db.register_user(message.from_user.id, full_name, email, "student", class_name)
        await message.answer(f"Привіт, {full_name}! Реєстрація успішна.", reply_markup=main_menu_for_student())
        await state.clear()
    else:
        await message.answer(
            f"Пошти {email} немає у списках {class_name} або дані некоректні.\nСпробуйте ще раз або /start",
            reply_markup=class_selection_menu()
        )

# --- Логіка Вчителя (Код -> Пошта -> Авто-ПІБ) ---

@router.message(F.text == "Вхід для вчителя")
async def teacher_auth_start(message: Message, state: FSMContext):
    await message.answer("Введіть секретний код доступу:", reply_markup=None)
    await state.set_state(AuthState.wait_for_teacher_code)

@router.message(AuthState.wait_for_teacher_code)
async def check_teacher_code(message: Message, state: FSMContext):
    if message.text == TEACHER_SECRET_CODE:
        await message.answer("Код вірний! Введіть вашу вчительську пошту:")
        await state.set_state(AuthState.wait_for_teacher_email)
    else:
        await message.answer("Невірний код. Спробуйте ще раз або /start")

@router.message(AuthState.wait_for_teacher_email)
async def process_teacher_email(message: Message, state: FSMContext):
    email = message.text.lower()
    # Шукаємо вчителя в allowed_emails (де class_name == 'teacher')
    user_data = db.get_allowed_user_data(email)
    
    if user_data and user_data[1] == 'teacher':
        full_name = user_data[0]
        db.register_user(message.from_user.id, full_name, email, "teacher")
        await message.answer(f"Вітаю, {full_name}!", reply_markup=main_menu_for_teacher())
        await state.clear()
    else:
        await message.answer("Цієї пошти немає в списку вчителів. Перевірте дані та спробуйте знову.")

# --- Функціонал для вчителя: Хто відсутній ---

@router.message(F.text == "Хто відсутній?")
async def teacher_absent_start(message: Message, state: FSMContext):
    if db.get_user_role(message.from_user.id) == "teacher":
        await message.answer("Оберіть клас для перевірки:", reply_markup=class_selection_menu())
        await state.set_state(AuthState.wait_for_absent_class)

# У файлі handlers/registr.py
@router.message(AuthState.wait_for_absent_class)
async def process_absent_check(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        return await cmd_start(message)
    
    selected_class = message.text
    absent_data = db.get_absent_students(selected_class)
    
    if not absent_data:
        await message.answer(f"У класі {selected_class} всі присутні! ✅", reply_markup=main_menu_for_teacher())
    else:
        # Просто з'єднуємо готові рядки символом нового рядка
        report = f"Відсутні у {selected_class}:\n" + "\n".join(absent_data)
        await message.answer(report, reply_markup=main_menu_for_teacher())
    
    await state.clear()

# --- Статуси, Візити та Вихід ---

@router.message(F.text.in_(["Прибув✅", "В дорозі🚗", "В дома🏠"]))
async def handle_student_status(message: Message):
    user_role = db.get_user_role(message.from_user.id)
    if user_role == "student":
        db.log_visit(message.from_user.id, message.text)
        # Підтвердження для учня
        await message.answer(f"Статус «{message.text}» успішно змінено! ✅")
    else:
        await message.answer("Ця функція доступна тільки учням.")

@router.message(F.text == "Показати всі візити")
async def show_all_visits(message: Message):
    if db.get_user_role(message.from_user.id) == "teacher":
        visits = db.get_all_today_visits()
        await message.answer(f"Журнал за сьогодні:\n{visits}")

@router.message(F.text == "Вийти з акаунта")
async def logout_to_test(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Ви вийшли з системи. Оберіть режим для входу:", reply_markup=regestration())

def register_handlers(dp):
    dp.include_router(router)