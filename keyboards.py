from urllib.parse import quote
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import ChoiceOption, City


def start_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💌 Створити запрошення", callback_data="inv:create")]
        ]
    )


def cities_kb(cities: list[City]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.button(text=f"📍 {city.name}", callback_data=f"inv:city:{city.id}")
    builder.adjust(2)
    return builder.as_markup()


def styles_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌹 Романтичний", callback_data="inv:style:romantic")],
            [
                InlineKeyboardButton(
                    text="😉 З гумором / легкий флірт", callback_data="inv:style:flirt"
                )
            ],
        ]
    )


def share_invite_kb(invite_link: str, share_text: str) -> InlineKeyboardMarkup:
    # Використовуємо t.me/share/url, щоб користувач міг швидко обрати чат і переслати посилання
    encoded_url = quote(invite_link, safe="")
    encoded_text = quote(share_text, safe="")
    share_url = f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поділитися запрошенням", url=share_url)],
            [InlineKeyboardButton(text="➕ Створити ще одне", callback_data="inv:create")],
        ]
    )


def survey_options_kb(step_prefix: str, options: list[ChoiceOption]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(text=opt.label, callback_data=f"srv:{step_prefix}:{opt.id}")
    builder.adjust(1)
    return builder.as_markup()


def confirm_survey_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Надіслати відповідь", callback_data="srv:send")],
            [InlineKeyboardButton(text="🔄 Пройти заново", callback_data="srv:restart")],
        ]
    )


def already_completed_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💌 Створити своє запрошення", callback_data="inv:create")]
        ]
    )


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
            [InlineKeyboardButton(text="📢 Розсилка", callback_data="adm:broadcast")],
            [InlineKeyboardButton(text="🏙️ Міста", callback_data="adm:cities")],
            [InlineKeyboardButton(text="🧩 Категорії вибору", callback_data="adm:categories")],
        ]
    )