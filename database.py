import uuid
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ChoiceOption(Base):
    __tablename__ = "choice_options"

    # category: "food" | "activity" | "day" | "time"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    allow_text_input: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(16), unique=True, index=True, default=lambda: uuid.uuid4().hex[:8]
    )
    sender_tg_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    recipient_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    city_name: Mapped[str] = mapped_column(String(64), nullable=False)
    style: Mapped[str] = mapped_column(String(32), nullable=False)  # "romantic" | "flirt"

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    food_choice: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_choice: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_choice: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_choice: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


DEFAULT_CITIES = ["Київ", "Львів", "Одеса", "Дніпро", "Харків", "Інше місто"]

DEFAULT_OPTIONS: list[tuple[str, str, bool]] = [
    ("food", "Кава та десерти", False),
    ("food", "Суші / Азія", False),
    ("food", "Бургери / Стріт-фуд", False),
    ("food", "Затишний ресторан", False),
    ("food", "Здивуй мене", False),

    ("activity", "Прогулянка парком / центром", False),
    ("activity", "Кіно", False),
    ("activity", "Настільні ігри / Антикафе", False),
    ("activity", "Виставка / Музей", False),
    ("activity", "Покататися на авто", False),
    ("activity", "На твій смак", False),

    ("day", "Сьогодні", False),
    ("day", "Завтра", False),
    ("day", "На вихідних", False),
    ("day", "Інший день", True),

    ("time", "Ранок", False),
    ("time", "День", False),
    ("time", "Вечір", False),
    ("time", "Конкретний час", True),
]


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        async with session.bind.begin() as conn:  # type: ignore[union-attr]
            await conn.run_sync(Base.metadata.create_all)

        existing_cities = (await session.execute(select(City.name))).scalars().all()
        for name in DEFAULT_CITIES:
            if name not in existing_cities:
                session.add(City(name=name, is_active=True))

        existing_opts = (
            await session.execute(select(ChoiceOption.category, ChoiceOption.label))
        ).all()
        existing_set = set(existing_opts)
        for cat, label, is_custom in DEFAULT_OPTIONS:
            if (cat, label) not in existing_set:
                session.add(
                    ChoiceOption(
                        category=cat,
                        label=label,
                        allow_text_input=is_custom,
                        is_active=True,
                    )
                )

        await session.commit()