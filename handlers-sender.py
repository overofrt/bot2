from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database import City, Invite
from keyboards import cities_kb, share_invite_kb, styles_kb
from states import SenderCreateInvite

router = Router()


@router.callback_query(F.data == "inv:create")
async def on_create_invite(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message or not callback.from_user:
        return

    async with session_factory() as session:
        cities = (
            await session.execute(
                select(City).where(City.is_active.is_(True)).order_by(City.id)
            )
        ).scalars().all()

    if not cities:
        await callback.answer("Список міст наразі порожній.", show_alert=True)
        return

    await state.set_state(SenderCreateInvite.choosing_city)
    await callback.message.edit_text(
        "📍 <b>Крок 1. Обери місто для зустрічі:</b>",
        reply_markup=cities_kb(list(cities)),
    )
    await callback.answer()


@router.callback_query(SenderCreateInvite.choosing_city, F.data.startswith("inv:city:"))
async def on_choose_city(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message or not callback.data:
        return

    try:
        city_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некоректний вибір. Обери місто зі списку.", show_alert=True)
        return

    async with session_factory() as session:
        city = await session.scalar(
            select(City).where(City.id == city_id, City.is_active.is_(True))
        )

    if city is None:
        await callback.answer("Це місто вже недоступне. Онови список.", show_alert=True)
        return

    await state.update_data(city_name=city.name)
    await state.set_state(SenderCreateInvite.choosing_style)
    await callback.message.edit_text(
        f"📍 Місто: <b>{city.name}</b>\n\n"
        f"🎭 <b>Крок 2. Обери стиль спілкування бота з отримувачем:</b>",
        reply_markup=styles_kb(),
    )
    await callback.answer()


@router.callback_query(SenderCreateInvite.choosing_style, F.data.startswith("inv:style:"))
async def on_choose_style(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message or not callback.from_user or not callback.data:
        return

    style_key = callback.data.split(":")[-1]
    if style_key not in {"romantic", "flirt"}:
        await callback.answer("Обери один із запропонованих стилів.", show_alert=True)
        return

    data = await state.get_data()
    city_name = data.get("city_name")
    if not city_name:
        await callback.answer("Сесія оновлена. Почни створення запрошення заново.", show_alert=True)
        await state.clear()
        return

    async with session_factory() as session:
        invite = Invite(
            sender_tg_id=callback.from_user.id,
            city_name=city_name,
            style=style_key,
        )
        session.add(invite)
        await session.commit()
        await session.refresh(invite)

    bot_info = await callback.bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={invite.code}"
    style_label = "🌹 Романтичний" if style_key == "romantic" else "😉 З гумором / легкий флірт"
    share_text = "Тримай запрошення — заповни 4 короткі пункти:"

    await state.clear()
    await callback.message.edit_text(
        f"💌 <b>Запрошення створено!</b>\n\n"
        f"• <b>ID запрошення:</b> <code>{invite.code}</code>\n"
        f"• <b>Місто:</b> {city_name}\n"
        f"• <b>Стиль:</b> {style_label}\n"
        f"• <b>Посилання:</b> <code>{invite_link}</code>",
        reply_markup=share_invite_kb(invite_link=invite_link, share_text=share_text),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inv:"))
async def on_stale_invite_callback(callback: CallbackQuery) -> None:
    # Захист від натискання старих кнопок після перезапуску або зміни стану
    await callback.answer(
        "Ця кнопка вже неактуальна. Натисни /start, щоб створити запрошення.",
        show_alert=True,
    )