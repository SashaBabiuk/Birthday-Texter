import os
import shutil
from configparser import ConfigParser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATABASE_PATH = DATA_DIR / "birthday_texter.db"
SESSION_PATH = DATA_DIR / "telegram.session"
LEGACY_SESSION_PATH = BASE_DIR / "src" / "data" / "bot.session"
TIMEZONE = os.getenv("TZ", "Europe/Kyiv")
SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", "60"))


def prepare_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SESSION_PATH.exists() and LEGACY_SESSION_PATH.exists():
        shutil.copy2(LEGACY_SESSION_PATH, SESSION_PATH)


def telegram_credentials() -> tuple[int | None, str | None]:
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    if not (api_id and api_hash):
        config = ConfigParser()
        config.read(BASE_DIR / "config.ini")
        api_id = config.get("Telegram", "api_id", fallback=None)
        api_hash = config.get("Telegram", "api_hash", fallback=None)
    try:
        return int(api_id) if api_id else None, api_hash
    except ValueError:
        return None, api_hash
