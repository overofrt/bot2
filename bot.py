import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DATABASE_URL
from database import create_session_factory, init_db
from handlers import admin, sender, start, survey


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise RuntimeError("Не задано BOT_TOKEN у змінних оточення або .env")

    session_factory = create_session_factory(DATABASE_URL)
    await init_db(session_factory)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp["session_factory"] = session_factory

    dp.include_router(admin.router)
    dp.include_router(sender.router)
    dp.include_router(start.router)
    dp.include_router(survey.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())