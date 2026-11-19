import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from aiohttp import web
from sqlalchemy import func, select

from config import ADMIN_IDS, BOT_TOKEN, DATABASE_URL, WEBAPP_URL
from database import City, Invite, create_session_factory, init_db

BASE_DIR = Path(__file__).resolve().parent


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    @dp.message(CommandStart())
    async def cmd_start(message: Message, bot: Bot) -> None:
        me = await bot.get_me()
        app_url = WEBAPP_URL or f"https://t.me/{me.username}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✨ Відкрити інтерфейс",
                        web_app=WebAppInfo(url=app_url) if app_url.startswith("https://") else None,
                        url=app_url if not app_url.startswith("https://") else None,
                    )
                ]
            ]
        )
        await message.answer(
            "<b>Date App</b> — відкрий інтерфейс, щоб створити запрошення або пройти 4 кроки побачення.",
            reply_markup=kb,
        )

    @dp.message(Command("stats"))
    async def cmd_stats(message: Message, session_factory) -> None:
        if ADMIN_IDS and message.from_user and message.from_user.id not in ADMIN_IDS:
            return
        async with session_factory() as session:
            total_invites = (await session.execute(select(func.count(Invite.id)))).scalar_one()
            completed_invites = (
                await session.execute(
                    select(func.count(Invite.id)).where(Invite.completed_at.is_not(None))
                )
            ).scalar_one()
        await message.answer(
            f"📊 <b>Статистика</b>\n"
            f"• Створено запрошень: <b>{total_invites}</b>\n"
            f"• Завершено 4 кроки: <b>{completed_invites}</b>"
        )

    @dp.message(F.web_app_data)
    async def on_webapp_data(message: Message) -> None:
        await message.answer(f"Отримано дані з Mini App: <code>{message.web_app_data.data}</code>")

    return dp


def build_web_app(bot: Bot, session_factory) -> web.Application:
    app = web.Application()

    async def index(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(BASE_DIR / "webapp" / "index.html")

    async def get_cities(_request: web.Request) -> web.Response:
        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(City.name).where(City.is_active.is_(True)).order_by(City.id)
                )
            ).scalars().all()
        return web.json_response({"cities": list(rows)})

    async def create_invite(request: web.Request) -> web.Response:
        payload = await request.json()
        city_name = str(payload.get("city_name") or "Київ").strip()
        style = str(payload.get("style") or "romantic").strip()
        sender_tg_id = int(payload.get("sender_tg_id") or 0)

        async with session_factory() as session:
            async with session.begin():
                invite = Invite(
                    sender_tg_id=sender_tg_id,
                    city_name=city_name,
                    style=style,
                )
                session.add(invite)
            await session.refresh(invite)

        me = await bot.get_me()
        webapp_link = (
            f"{WEBAPP_URL.rstrip('/')}?invite={invite.code}"
            if WEBAPP_URL
            else f"https://t.me/{me.username}?start={invite.code}"
        )
        bot_link = f"https://t.me/{me.username}?start={invite.code}"

        return web.json_response(
            {
                "code": invite.code,
                "city_name": invite.city_name,
                "style": invite.style,
                "webapp_link": webapp_link,
                "bot_link": bot_link,
            }
        )

    async def get_invite(request: web.Request) -> web.Response:
        code = request.match_info["code"]
        async with session_factory() as session:
            invite = (
                await session.execute(select(Invite).where(Invite.code == code))
            ).scalar_one_or_none()

        if not invite:
            return web.json_response({"error": "Запрошення не знайдено"}, status=404)

        return web.json_response(
            {
                "code": invite.code,
                "city_name": invite.city_name,
                "style": invite.style,
                "food": invite.food,
                "activity": invite.activity,
                "day": invite.day,
                "time_slot": invite.time_slot,
                "note": invite.note,
                "completed": invite.completed_at is not None,
            }
        )

    async def complete_invite(request: web.Request) -> web.Response:
        code = request.match_info["code"]
        payload = await request.json()

        food = str(payload.get("food") or "").strip()
        activity = str(payload.get("activity") or "").strip()
        day = str(payload.get("day") or "").strip()
        time_slot = str(payload.get("time_slot") or "").strip()
        note = str(payload.get("note") or "").strip()

        async with session_factory() as session:
            async with session.begin():
                invite = (
                    await session.execute(select(Invite).where(Invite.code == code))
                ).scalar_one_or_none()
                if not invite:
                    return web.json_response({"error": "Запрошення не знайдено"}, status=404)

                invite.food = food
                invite.activity = activity
                invite.day = day
                invite.time_slot = time_slot
                invite.note = note
                invite.completed_at = datetime.utcnow()

        if invite.sender_tg_id:
            summary = (
                f"💌 <b>Запрошення підтверджено!</b>\n\n"
                f"📍 Місто: <b>{invite.city_name}</b>\n"
                f"🍽 Формат їжі: <b>{food}</b>\n"
                f"✨ Активність: <b>{activity}</b>\n"
                f"📅 День: <b>{day}</b>\n"
                f"⏰ Час: <b>{time_slot}</b>"
            )
            if note:
                summary += f"\n📝 Нотатка: <i>{note}</i>"
            try:
                await bot.send_message(chat_id=invite.sender_tg_id, text=summary)
            except Exception as exc:
                logging.warning("Не вдалося надіслати повідомлення відправнику: %s", exc)

        return web.json_response({"ok": True})

    app.router.add_get("/", index)
    app.router.add_get("/api/cities", get_cities)
    app.router.add_post("/api/invites", create_invite)
    app.router.add_get("/api/invites/{code}", get_invite)
    app.router.add_post("/api/invites/{code}/complete", complete_invite)
    return app


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise RuntimeError("Не вказано BOT_TOKEN у змінних оточення")

    session_factory = create_session_factory(DATABASE_URL)
    await init_db(session_factory)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()
    dp["session_factory"] = session_factory

    if WEBAPP_URL.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="✨ Відкрити",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        )

    app = build_web_app(bot, session_factory)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info("Web App сервер запущено на порту %s", port)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
