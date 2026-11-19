import asyncio
import logging
import os
from pathlib import Path
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo
from sqlalchemy import select

from config import BOT_TOKEN, DATABASE_URL
from database import City, Invite, create_session_factory, init_db
from handlers import admin, sender, start, survey

BASE_DIR = Path(__file__).resolve().parent


async def build_web_app(bot: Bot, session_factory) -> web.Application:
    app = web.Application()

    async def index(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(BASE_DIR / "webapp" / "index.html")

    async def get_cities(_request: web.Request) -> web.Response:
        async with session_factory() as session:
            cities = (
                await session.execute(
                    select(City.name).where(City.is_active.is_(True)).order_by(City.id)
                )
            ).scalars().all()
        return web.json_response({"cities": list(cities)})

    async def create_invite(request: web.Request) -> web.Response:
        payload = await request.json()
        async with session_factory() as session:
            invite = Invite(
                sender_tg_id=int(payload.get("sender_tg_id", 0)),
                city_name=str(payload.get("city_name", "Київ")),
                style=str(payload.get("style", "romantic")),
            )
            session.add(invite)
            await session.commit()
            await session.refresh(invite)

        me = await bot.get_me()
        link = f"https://t.me/{me.username}?start={invite.code}"
        return web.json_response({"code": invite.code, "invite_link": link})

    app.router.add_get("/", index)
    app.router.add_get("/api/cities", get_cities)
    app.router.add_post("/api/invites", create_invite)
    return app


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise RuntimeError("Не задано BOT_TOKEN")

    session_factory = create_session_factory(DATABASE_URL)
    await init_db(session_factory)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp["session_factory"] = session_factory

    dp.include_router(admin.router)
    dp.include_router(sender.router)
    dp.include_router(start.router)
    dp.include_router(survey.router)

    webapp_url = os.getenv("WEBAPP_URL", "").strip()
    if webapp_url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="💌 Відкрити",
                web_app=WebAppInfo(url=webapp_url),
            )
        )

    app = await build_web_app(bot, session_factory)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
