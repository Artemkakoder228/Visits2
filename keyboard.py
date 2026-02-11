from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def regestration():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Реєстрація"), KeyboardButton(text="Авторизація")]
        ],
        resize_keyboard=True
    )

# keyboard.py
def main_menu_for_teacher():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Показати всі візити")],
            [KeyboardButton(text="Хто відсутній?")], # Нова кнопка
            [KeyboardButton(text="Вийти з акаунта")]
        ],
        resize_keyboard=True
    )

def main_menu_for_student():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Прибув✅")],
            [KeyboardButton(text="В дорозі🚗")],
            [KeyboardButton(text="В дома🏠")],
            [KeyboardButton(text="Вийти з акаунта")] # Додано
        ],
        resize_keyboard=True
    )

def regestration():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Учень: Реєстрація за email")],
            [KeyboardButton(text="Вхід для вчителя")]
        ],
        resize_keyboard=True
    )

def class_selection_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="10-А")],
            [KeyboardButton(text="⬅️ Назад")] # Текст має збігатися з F.text
        ],
        resize_keyboard=True
    )

