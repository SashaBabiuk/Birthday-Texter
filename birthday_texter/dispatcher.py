import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from .config import TIMEZONE
from .database import engine
from .models import Birthday, SendHistory, utcnow
from .telegram import telegram

logger = logging.getLogger(__name__)
dispatch_lock = asyncio.Lock()


async def send_birthday(birthday_id: int, recipient: str | None = None, mark_sent: bool = False) -> bool:
    async with dispatch_lock:
        with Session(engine) as session:
            birthday = session.get(Birthday, birthday_id)
            if not birthday:
                return False
            destination = recipient or birthday.telegram_recipient
            try:
                await telegram.send(destination, birthday.message)
            except Exception as exc:
                session.add(SendHistory(
                    birthday_id=birthday.id, recipient=destination, message=birthday.message,
                    status="failed", error=str(exc),
                ))
                session.commit()
                logger.warning("Birthday send failed for %s: %s", birthday.name, exc)
                return False

            if mark_sent:
                birthday.last_sent_year = datetime.now(ZoneInfo(TIMEZONE)).year
                birthday.updated_at = utcnow()
                session.add(birthday)
            session.add(SendHistory(
                birthday_id=birthday.id, recipient=destination, message=birthday.message,
                status="sent",
            ))
            session.commit()
            return True


async def dispatch_due_birthdays() -> None:
    now = datetime.now(ZoneInfo(TIMEZONE))
    with Session(engine) as session:
        due_ids = [birthday.id for birthday in session.exec(select(Birthday).where(
            Birthday.enabled == True,  # noqa: E712
            Birthday.birthday_month == now.month,
            Birthday.birthday_day == now.day,
            Birthday.send_time <= now.strftime("%H:%M"),
            (Birthday.last_sent_year.is_(None)) | (Birthday.last_sent_year != now.year),
        )).all()]
    for birthday_id in due_ids:
        await send_birthday(birthday_id, mark_sent=True)
