import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=lambda: uuid.uuid4().hex[:10]
    )
    sender_tg_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    city_name: Mapped[str] = mapped_column(String(100), nullable=False)
    style: Mapped[str] = mapped_column(String(32), default="romantic", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    food: Mapped[str | None] = mapped_column(String(120), nullable=True)
    activity: Mapped[str | None] = mapped_column(String(120), nullable=True)
    day: Mapped[str | None] = mapped_column(String(120), nullable=True)
    time_slot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(normalize_db_url(database_url), echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


DEFAULT_CITIES = [
    "Київ",
    "Львів",
    "Одеса"
    "Дніпро",
    "Рівне",
    "Харків",
    "Вінниця",
    "Хмельницький",
]


async def init_db(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        engine = session.bind
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session.begin():
            existing = (await session.execute(select(City.id).limit(1))).first()
            if not existing:
                for city_name in DEFAULT_CITIES:
                    session.add(City(name=city_name, is_active=True))
