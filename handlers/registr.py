from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
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
    user_role = await db.get_user_role(message.from_user.id) # Додано await
    
    if user_role == "teacher":
        await message.answer("Вітаю, вчителю!", reply_markup=main_menu_for_teacher())
    elif user_role == "student":
        await message.answer("Привіт! Оберіть статус:", reply_markup=main_menu_for_student())
    else:
        await message.answer("Вітаємо у системі Visits!", reply_markup=regestration())

@router.message(F.text == "Учень: Реєстрація за email")
async def student_reg_start(message: Message, state: FSMContext):
    await state.clear() 
    await message.answer("Оберіть ваш клас:", reply_markup=class_selection_menu())
    await state.set_state(db.AuthState.wait_for_class)

@router.message(db.AuthState.wait_for_email)
async def process_email(message: Message, state: FSMContext):
    email = message.text.lower()
    data = await state.get_data()
    class_name = data.get('class_name')
    
    user_data = await db.get_allowed_user_data(email) # Додано await
    
    if user_data and user_data[1] == class_name:
        full_name = user_data[0]
        await db.register_user(message.from_user.id, full_name, email, "student", class_name) # Додано await
        await message.answer(f"Привіт, {full_name}! Реєстрація успішна.", reply_markup=main_menu_for_student())
        await state.clear()
    else:
        await message.answer(f"Пошти {email} немає у списках {class_name}.", reply_markup=class_selection_menu())

@router.message(db.AuthState.wait_for_teacher_email)
async def process_teacher_email(message: Message, state: FSMContext):
    email = message.text.lower()
    user_data = await db.get_allowed_user_data(email) # Додано await
    
    if user_data and user_data[1] == 'teacher':
        await db.register_user(message.from_user.id, user_data[0], email, "teacher") # Додано await
        await message.answer(f"Вітаю, {user_data[0]}!", reply_markup=main_menu_for_teacher())
        await state.clear()
    else:
        await message.answer("Цієї пошти немає в списку вчителів.")

@router.message(F.text == "Хто відсутній?")
async def teacher_absent_start(message: Message, state: FSMContext):
    if await db.get_user_role(message.from_user.id) == "teacher": # Додано await
        await message.answer("Оберіть клас:", reply_markup=class_selection_menu())
        await state.set_state(db.AuthState.wait_for_absent_class)

@router.message(db.AuthState.wait_for_absent_class)
async def process_absent_check(message: Message, state: FSMContext):
    absent_data = await db.get_absent_students(message.text) # Додано await
    if not absent_data:
        await message.answer("Всі присутні! ✅", reply_markup=main_menu_for_teacher())
    else:
        report = f"Відсутні у {message.text}:\n" + "\n".join(absent_data)
        await message.answer(report, reply_markup=main_menu_for_teacher())
    await state.clear()

@router.message(F.text.in_(["Прибув✅", "В дорозі🚗", "В дома🏠"]))
async def handle_student_status(message: Message):
    if await db.get_user_role(message.from_user.id) == "student": # Додано await
        await db.log_visit(message.from_user.id, message.text) # Додано await
        await message.answer(f"Статус «{message.text}» змінено! ✅")

@router.message(F.text == "Показати всі візити")
async def show_all_visits(message: Message):
    if await db.get_user_role(message.from_user.id) == "teacher": # Додано await
        visits = await db.get_all_today_visits() # Додано await
        await message.answer(f"Журнал за сьогодні:\n{visits}")