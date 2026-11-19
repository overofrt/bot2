import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dates.db").strip()
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "").strip()
ADMIN_IDS: set[int] = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
