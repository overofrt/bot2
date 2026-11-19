from html import escape


def format_user_mention(tg_id: int, full_name: str, username: str | None) -> str:
    safe_name = escape(full_name)
    if username:
        return f'<a href="tg://user?id={tg_id}">{safe_name}</a> (@{escape(username)})'
    return f'<a href="tg://user?id={tg_id}">{safe_name}</a>'


def recipient_greeting_text(style: str, sender_name: str, city_name: str) -> str:
    name = escape(sender_name)
    city = escape(city_name)
    if style == "flirt":
        return (
            f"👀 Привіт! Схоже, <b>{name}</b> вирішив(-ла) не тягнути інтригу "
            f"та надіслав(-ла) тобі запрошення на побачення (місто: <b>{city}</b>).\n\n"
            f"Зберемо формат зустрічі у 4 легкі кліки — без зайвих «ну давай подумаємо» 😉"
        )
    return (
        f"✨ Привіт!\n"
        f"<b>{name}</b> надіслав(-ла) тобі тепле запрошення на зустріч у місті <b>{city}</b>.\n\n"
        f"Пройди коротке опитування з 4 кроків, щоб ми могли обрати найкомфортніший формат 💌"
    )


def build_checklist_text(
    invite_code: str,
    city_name: str,
    recipient_mention: str,
    food: str,
    activity: str,
    day: str,
    time: str,
) -> str:
    return (
        f"🎉 <b>Запрошення #{escape(invite_code)} прийнято!</b>\n"
        f"👤 Отримувач: {recipient_mention}\n"
        f"📍 Місто: <b>{escape(city_name)}</b>\n\n"
        f"📋 <b>Чек-лист побачення:</b>\n"
        f"• <b>Їжа / напої:</b> {escape(food)}\n"
        f"• <b>Активність:</b> {escape(activity)}\n"
        f"• <b>Бажаний день:</b> {escape(day)}\n"
        f"• <b>Зручний час:</b> {escape(time)}"
    )