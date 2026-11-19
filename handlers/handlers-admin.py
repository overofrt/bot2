import asyncio
from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import ADMIN_IDS
from database import ChoiceOption, City, Invite, User
from keyboards import admin_main_kb
from states import AdminPanelState

router = Router()


class AdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return bool(event.from_user and event.from_user.id in ADMIN_IDS)


@router.message(Command("admin"), AdminFilter())
async def open_admin_panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🛠️ <b>Адмін-панель</b>", reply_markup=admin_main_kb())


@router.callback_query(F.data == "adm:stats", AdminFilter())
async def admin_stats(
    callback: CallbackQuery, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    if not callback.message:
        return
    async with session_factory() as session:
        total_users = await session.scalar(select(func.count(User.id))) or 0
        total_invites = await session.scalar(select(func.count(Invite.id))) or 0
        completed_invites = (
            await session.scalar(select(func.count(Invite.id)).where(Invite.is_completed.is_(True)))
            or 0
        )

    await callback.message.edit_text(
        f"📊 <b>Статистика бота</b>\n\n"
        f"• Користувачів: <b>{total_users}</b>\n"
        f"• Створено запрошень: <b>{total_invites}</b>\n"
        f"• Завершено анкет: <b>{completed_invites}</b>",
        reply_markup=admin_main_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:broadcast", AdminFilter())
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return
    await state.set_state(AdminPanelState.waiting_broadcast_text)
    await callback.message.edit_text("📢 Надішли текст повідомлення для розсилки всім користувачам:")
    await callback.answer()


@router.message(AdminPanelState.waiting_broadcast_text, AdminFilter())
async def admin_broadcast_run(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ Повідомлення не може бути порожнім.")
        return

    await state.clear()
    async with session_factory() as session:
        user_ids = (await session.execute(select(User.tg_id))).scalars().all()

    sent = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await message.answer(
        f"✅ Розсилку завершено. Доставлено: <b>{sent}</b> із <b>{len(user_ids)}</b>.",
        reply_markup=admin_main_kb(),
    )


@router.callback_query(F.data == "adm:cities", AdminFilter())
async def admin_cities_list(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message:
        return
    async with session_factory() as session:
        cities = (await session.execute(select(City).order_by(City.id))).scalars().all()

    lines = [
        f"{'🟢' if c.is_active else '🔴'} <code>{c.id}</code>. {c.name}" for c in cities
    ]
    await state.set_state(AdminPanelState.waiting_new_city)
    await callback.message.edit_text(
        "🏙️ <b>Міста</b> (🟢 активне / 🔴 вимкнене):\n"
        + ("\n".join(lines) if lines else "Порожньо")
        + "\n\nНадішли назву нового міста, щоб додати його, або надішли <code>-ID</code> щоб вимкнути (наприклад: <code>-3</code>):",
        reply_markup=admin_main_kb(),
    )
    await callback.answer()


@router.message(AdminPanelState.waiting_new_city, AdminFilter())
async def admin_city_mutate(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    raw = (message.text or "").strip()
    if not raw:
        return

    async with session_factory() as session:
        if raw.startswith("-") and raw[1:].isdigit():
            city_id = int(raw[1:])
            city = await session.scalar(select(City).where(City.id == city_id))
            if city:
                city.is_active = False
                await session.commit()
                await message.answer(f"🔴 Місто «{city.name}» вимкнено.", reply_markup=admin_main_kb())
            else:
                await message.answer("⚠️ Місто з таким ID не знайдено.")
        else:
            existing = await session.scalar(select(City).where(City.name == raw))
            if existing:
                existing.is_active = True
            else:
                session.add(City(name=raw, is_active=True))
            await session.commit()
            await message.answer(f"🟢 Місто «{raw}» додано та активовано.", reply_markup=admin_main_kb())

    await state.clear()


@router.callback_query(F.data == "adm:categories", AdminFilter())
async def admin_categories_info(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message:
        return
    async with session_factory() as session:
        opts = (
            await session.execute(select(ChoiceOption).order_by(ChoiceOption.category, ChoiceOption.id))
        ).scalars().all()

    lines = [
        f"{'🟢' if o.is_active else '🔴'} <code>{o.id}</code> [{o.category}] {o.label}"
        for o in opts
    ]
    await state.set_state(AdminPanelState.waiting_new_option_label)
    await callback.message.edit_text(
        "🧩 <b>Варіанти вибору</b>:\n"
        + "\n".join(lines[:30])
        + "\n\nЩоб додати варіант: <code>категорія | назва</code> (категорії: <code>food</code>, <code>activity</code>, <code>day</code>, <code>time</code>).\n"
        "Щоб вимкнути варіант: <code>-ID</code> (наприклад: <code>-2</code>).",
        reply_markup=admin_main_kb(),
    )
    await callback.answer()


@router.message(AdminPanelState.waiting_new_option_label, AdminFilter())
async def admin_option_mutate(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    raw = (message.text or "").strip()
    valid_cats = {"food", "activity", "day", "time"}

    async with session_factory() as session:
        if raw.startswith("-") and raw[1:].isdigit():
            opt = await session.scalar(select(ChoiceOption).where(ChoiceOption.id == int(raw[1:])))
            if opt:
                opt.is_active = False
                await session.commit()
                await message.answer(f"🔴 Варіант «{opt.label}» вимкнено.", reply_markup=admin_main_kb())
            else:
                await message.answer("⚠️ Варіант не знайдено.")
        elif "|" in raw:
            cat, label = [part.strip() for part in raw.split("|", 1)]
            if cat not in valid_cats or not label:
                await message.answer("⚠️ Формат: <code>food | Назва варіанту</code>")
                return
            session.add(ChoiceOption(category=cat, label=label, allow_text_input=False, is_active=True))
            await session.commit()
            await message.answer(f"🟢 Додано «{label}» у категорію <code>{cat}</code>.", reply_markup=admin_main_kb())
        else:
            await message.answer("⚠️ Використовуй формат <code>food | Назва</code> або <code>-ID</code>.")
            return

    await state.clear()