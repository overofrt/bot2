from datetime import datetime
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database import ChoiceOption, Invite
from keyboards import already_completed_kb, confirm_survey_kb, survey_options_kb
from states import RecipientSurvey
from texts import build_checklist_text, format_user_mention

router = Router()


async def _get_active_options(
    session_factory: async_sessionmaker[AsyncSession], category: str
) -> list[ChoiceOption]:
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(ChoiceOption)
                .where(ChoiceOption.category == category, ChoiceOption.is_active.is_(True))
                .order_by(ChoiceOption.id)
            )
        ).scalars().all()
    return list(rows)


def _summary_text(data: dict) -> str:
    return (
        "📋 <b>Перевір свій вибір перед відправкою:</b>\n\n"
        f"• <b>Їжа / напої:</b> {data.get('food')}\n"
        f"• <b>Активність:</b> {data.get('activity')}\n"
        f"• <b>Бажаний день:</b> {data.get('day')}\n"
        f"• <b>Зручний час:</b> {data.get('time')}"
    )


@router.callback_query(RecipientSurvey.step_food, F.data.startswith("srv:food:"))
async def step_food_chosen(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message or not callback.data:
        return
    opt_id = int(callback.data.split(":")[-1])
    async with session_factory() as session:
        opt = await session.scalar(select(ChoiceOption).where(ChoiceOption.id == opt_id))
    if not opt:
        await callback.answer("Варіант не знайдено.", show_alert=True)
        return

    await state.update_data(food=opt.label)
    activities = await _get_active_options(session_factory, "activity")
    await state.set_state(RecipientSurvey.step_activity)
    await callback.message.edit_text(
        "<b>Крок 2/4. Активність:</b>",
        reply_markup=survey_options_kb("activity", activities),
    )
    await callback.answer()


@router.callback_query(RecipientSurvey.step_activity, F.data.startswith("srv:activity:"))
async def step_activity_chosen(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message or not callback.data:
        return
    opt_id = int(callback.data.split(":")[-1])
    async with session_factory() as session:
        opt = await session.scalar(select(ChoiceOption).where(ChoiceOption.id == opt_id))
    if not opt:
        await callback.answer("Варіант не знайдено.", show_alert=True)
        return

    await state.update_data(activity=opt.label)
    days = await _get_active_options(session_factory, "day")
    await state.set_state(RecipientSurvey.step_day)
    await callback.message.edit_text(
        "<b>Крок 3/4. Бажаний день:</b>",
        reply_markup=survey_options_kb("day", days),
    )
    await callback.answer()


@router.callback_query(RecipientSurvey.step_day, F.data.startswith("srv:day:"))
async def step_day_chosen(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message or not callback.data:
        return
    opt_id = int(callback.data.split(":")[-1])
    async with session_factory() as session:
        opt = await session.scalar(select(ChoiceOption).where(ChoiceOption.id == opt_id))
    if not opt:
        await callback.answer("Варіант не знайдено.", show_alert=True)
        return

    if opt.allow_text_input:
        await state.set_state(RecipientSurvey.step_day_custom)
        await callback.message.edit_text(
            "✍️ Введи бажаний день текстом (наприклад: <i>п'ятниця</i> або <i>24 листопада</i>):"
        )
        await callback.answer()
        return

    await state.update_data(day=opt.label)
    times = await _get_active_options(session_factory, "time")
    await state.set_state(RecipientSurvey.step_time)
    await callback.message.edit_text(
        "<b>Крок 4/4. Зручний час:</b>",
        reply_markup=survey_options_kb("time", times),
    )
    await callback.answer()


@router.message(RecipientSurvey.step_day_custom)
async def step_day_custom_text(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    text = (message.text or "").strip()
    if not text or len(text) > 80:
        await message.answer("⚠️ Введи короткий опис дня (до 80 символів).")
        return

    await state.update_data(day=text)
    times = await _get_active_options(session_factory, "time")
    await state.set_state(RecipientSurvey.step_time)
    await message.answer(
        "<b>Крок 4/4. Зручний час:</b>",
        reply_markup=survey_options_kb("time", times),
    )


@router.callback_query(RecipientSurvey.step_time, F.data.startswith("srv:time:"))
async def step_time_chosen(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message or not callback.data:
        return
    opt_id = int(callback.data.split(":")[-1])
    async with session_factory() as session:
        opt = await session.scalar(select(ChoiceOption).where(ChoiceOption.id == opt_id))
    if not opt:
        await callback.answer("Варіант не знайдено.", show_alert=True)
        return

    if opt.allow_text_input:
        await state.set_state(RecipientSurvey.step_time_custom)
        await callback.message.edit_text(
            "✍️ Введи зручний час текстом (наприклад: <i>о 19:30</i> або <i>після 18:00</i>):"
        )
        await callback.answer()
        return

    await state.update_data(time=opt.label)
    data = await state.get_data()
    await state.set_state(RecipientSurvey.confirm)
    await callback.message.edit_text(_summary_text(data), reply_markup=confirm_survey_kb())
    await callback.answer()


@router.message(RecipientSurvey.step_time_custom)
async def step_time_custom_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text or len(text) > 80:
        await message.answer("⚠️ Введи зручний час текстом (до 80 символів).")
        return

    await state.update_data(time=text)
    data = await state.get_data()
    await state.set_state(RecipientSurvey.confirm)
    await message.answer(_summary_text(data), reply_markup=confirm_survey_kb())


@router.callback_query(RecipientSurvey.confirm, F.data == "srv:restart")
async def restart_survey(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message:
        return
    foods = await _get_active_options(session_factory, "food")
    await state.set_state(RecipientSurvey.step_food)
    await callback.message.edit_text(
        "<b>Крок 1/4. Формат їжі / напоїв:</b>",
        reply_markup=survey_options_kb("food", foods),
    )
    await callback.answer()


@router.callback_query(RecipientSurvey.confirm, F.data == "srv:send")
async def submit_survey(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if not callback.message or not callback.from_user:
        return

    data = await state.get_data()
    invite_code = data.get("invite_code")
    if not invite_code:
        await callback.answer("Дані опитування не знайдено.", show_alert=True)
        return

    async with session_factory() as session:
        invite = await session.scalar(select(Invite).where(Invite.code == invite_code))
        if invite is None or invite.is_completed:
            await state.clear()
            await callback.message.edit_text(
                "✨ Це запрошення вже було завершено раніше.",
                reply_markup=already_completed_kb(),
            )
            await callback.answer()
            return

        invite.recipient_tg_id = callback.from_user.id
        invite.food_choice = data.get("food")
        invite.activity_choice = data.get("activity")
        invite.day_choice = data.get("day")
        invite.time_choice = data.get("time")
        invite.is_completed = True
        invite.completed_at = datetime.utcnow()
        await session.commit()

    await state.clear()
    await callback.message.edit_text(
        "✅ Відповідь надіслана! Гарної зустрічі ✨",
        reply_markup=already_completed_kb(),
    )

    recipient_mention = format_user_mention(
        tg_id=callback.from_user.id,
        full_name=callback.from_user.full_name,
        username=callback.from_user.username,
    )
    checklist = build_checklist_text(
        invite_code=invite.code,
        city_name=invite.city_name,
        recipient_mention=recipient_mention,
        food=data.get("food", "-"),
        activity=data.get("activity", "-"),
        day=data.get("day", "-"),
        time=data.get("time", "-"),
    )
    try:
        await callback.bot.send_message(chat_id=invite.sender_tg_id, text=checklist)
    except Exception:
        pass

    await callback.answer()

@router.message(
    RecipientSurvey.step_food,
    RecipientSurvey.step_activity,
    RecipientSurvey.step_day,
    RecipientSurvey.step_time,
)
async def text_instead_of_button(message: Message) -> None:
    await message.answer("👇 Будь ласка, обери один із варіантів на кнопках під повідомленням.")


@router.callback_query(F.data.startswith("srv:"))
async def stale_survey_button(callback: CallbackQuery) -> None:
    await callback.answer(
        "Ця кнопка вже неактуальна. Перейди за запрошенням ще раз або натисни /start.",
        show_alert=True,
    )
