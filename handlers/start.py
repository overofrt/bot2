from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database import ChoiceOption, Invite, User
from keyboards import already_completed_kb, start_menu_kb, survey_options_kb
from states import RecipientSurvey
from texts import recipient_greeting_text

router = Router()


async def upsert_user(
    session_factory: async_sessionmaker[AsyncSession],
    tg_id: int,
    full_name: str,
    username: str | None,
) -> None:
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user is None:
            session.add(
                User(tg_id=tg_id, full_name=full_name or "Користувач", username=username)
            )
        else:
            user.full_name = full_name or user.full_name
            user.username = username
        await session.commit()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not message.from_user:
        return

    await state.clear()
    await upsert_user(
        session_factory=session_factory,
        tg_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )

    payload = (command.args or "").strip()
    if not payload:
        await message.answer(
            "👋 Привіт! Це бот для легких і невимушених запрошень на побачення.\n\n"
            "Створи персональне посилання, обери місто та стиль — і надішли його тому, "
            "з ким хочеш провести час.",
            reply_markup=start_menu_kb(),
        )
        return

    async with session_factory() as session:
        invite = await session.scalar(select(Invite).where(Invite.code == payload))
        if invite is None:
            await message.answer(
                "⚠️ Це запрошення не знайдено або воно вже неактивне.",
                reply_markup=start_menu_kb(),
            )
            return

        if invite.is_completed:
            await message.answer(
                "✨ Відповідь за цим запрошенням уже надіслана! "
                "Але ти можеш створити власне запрошення.",
                reply_markup=already_completed_kb(),
            )
            return

        sender = await session.scalar(select(User).where(User.tg_id == invite.sender_tg_id))
        sender_name = sender.full_name if sender else "Відправник"
        food_options = (
            await session.execute(
                select(ChoiceOption)
                .where(ChoiceOption.category == "food", ChoiceOption.is_active.is_(True))
                .order_by(ChoiceOption.id)
            )
        ).scalars().all()

    await state.set_state(RecipientSurvey.step_food)
    await state.update_data(invite_code=invite.code)

    greeting = recipient_greeting_text(
        style=invite.style, sender_name=sender_name, city_name=invite.city_name
    )
    await message.answer(greeting)
    await message.answer(
        "<b>Крок 1/4. Формат їжі / напоїв:</b>",
        reply_markup=survey_options_kb("food", list(food_options)),
    )