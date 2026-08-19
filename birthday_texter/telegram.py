import asyncio
import logging

from telethon import TelegramClient

from .config import SESSION_PATH, telegram_credentials

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self) -> None:
        self.client: TelegramClient | None = None
        self.error: str | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        api_id, api_hash = telegram_credentials()
        if not api_id or not api_hash:
            self.error = "Telegram API credentials are not configured"
            return
        try:
            self.client = TelegramClient(str(SESSION_PATH.with_suffix("")), api_id, api_hash)
            await self.client.connect()
            if not await self.client.is_user_authorized():
                self.error = "Telegram session is not authorized"
        except Exception as exc:  # surfaced on the status page
            self.error = str(exc)
            logger.exception("Could not connect to Telegram")

    async def disconnect(self) -> None:
        if self.client:
            await self.client.disconnect()

    async def send(self, recipient: str, message: str) -> None:
        async with self._lock:
            if not self.client or not self.client.is_connected():
                raise RuntimeError(self.error or "Telegram is not connected")
            if not await self.client.is_user_authorized():
                raise RuntimeError("Telegram session is not authorized")
            target: int | str = int(recipient) if recipient.lstrip("-").isdigit() else recipient
            await self.client.send_message(target, message)

    async def status(self) -> dict[str, str | bool | None]:
        if not self.client or not self.client.is_connected():
            return {"connected": False, "account": None, "error": self.error}
        try:
            if not await self.client.is_user_authorized():
                return {"connected": False, "account": None, "error": self.error}
            me = await self.client.get_me()
            account = f"@{me.username}" if me.username else (me.first_name or str(me.id))
            return {"connected": True, "account": account, "error": None}
        except Exception as exc:
            return {"connected": False, "account": None, "error": str(exc)}


telegram = TelegramService()
