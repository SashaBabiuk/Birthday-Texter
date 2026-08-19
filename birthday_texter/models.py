from datetime import datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.utcnow()


class Birthday(SQLModel, table=True):
    __tablename__ = "birthdays"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    telegram_recipient: str = Field(index=True)
    birthday_month: int
    birthday_day: int
    send_time: str
    message: str
    enabled: bool = True
    last_sent_year: int | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SendHistory(SQLModel, table=True):
    __tablename__ = "send_history"

    id: int | None = Field(default=None, primary_key=True)
    birthday_id: int | None = Field(default=None, foreign_key="birthdays.id", index=True)
    attempted_at: datetime = Field(default_factory=utcnow, index=True)
    recipient: str
    message: str
    status: str = Field(index=True)
    error: str | None = None


class Setting(SQLModel, table=True):
    __tablename__ = "settings"

    key: str = Field(primary_key=True)
    value: str
