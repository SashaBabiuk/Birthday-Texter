from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from .config import SCHEDULER_INTERVAL, TIMEZONE
from .database import create_db_and_tables, get_session
from .dispatcher import dispatch_due_birthdays, send_birthday
from .models import Birthday, SendHistory, utcnow
from .telegram import telegram

PACKAGE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    await telegram.connect()
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(dispatch_due_birthdays, "interval", seconds=SCHEDULER_INTERVAL,
                      id="birthday-dispatcher", max_instances=1, coalesce=True)
    scheduler.start()
    await dispatch_due_birthdays()
    yield
    scheduler.shutdown(wait=False)
    await telegram.disconnect()


app = FastAPI(title="Birthday Texter", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")


def redirect(path: str, notice: str | None = None) -> RedirectResponse:
    suffix = f"?notice={notice}" if notice else ""
    return RedirectResponse(path + suffix, status_code=303)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: Session = Depends(get_session)):
    now = datetime.now(ZoneInfo(TIMEZONE))
    birthdays = session.exec(select(Birthday)).all()
    today = [b for b in birthdays if (b.birthday_month, b.birthday_day) == (now.month, now.day)]
    upcoming = []
    for birthday in birthdays:
        try:
            occurrence = date(now.year, birthday.birthday_month, birthday.birthday_day)
        except ValueError:
            occurrence = date(now.year, 2, 28)
        if occurrence < now.date():
            occurrence = occurrence.replace(year=now.year + 1)
        upcoming.append((occurrence, birthday.send_time, birthday))
    upcoming.sort(key=lambda item: (item[0], item[1]))
    week_end = now.date() + timedelta(days=7)
    history = session.exec(select(SendHistory).order_by(SendHistory.attempted_at.desc()).limit(8)).all()
    return templates.TemplateResponse(request, "dashboard.html", {
        "birthdays": birthdays, "today": today,
        "week_count": sum(1 for item in upcoming if item[0] <= week_end),
        "next_birthday": upcoming[0] if upcoming else None,
        "history": history, "telegram_status": await telegram.status(), "timezone": TIMEZONE,
    })


@app.get("/birthdays", response_class=HTMLResponse)
def birthdays_list(request: Request, session: Session = Depends(get_session)):
    birthdays = session.exec(select(Birthday).order_by(Birthday.name)).all()
    return templates.TemplateResponse(request, "birthdays.html", {"birthdays": birthdays})


@app.get("/birthdays/new", response_class=HTMLResponse)
def birthday_new(request: Request):
    return templates.TemplateResponse(request, "birthday_form.html", {"birthday": None})


@app.get("/birthdays/{birthday_id}/edit", response_class=HTMLResponse)
def birthday_edit(birthday_id: int, request: Request, session: Session = Depends(get_session)):
    birthday = session.get(Birthday, birthday_id)
    if not birthday:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "birthday_form.html", {"birthday": birthday})


def apply_form(birthday: Birthday, name: str, telegram_recipient: str, birthday_month: int,
               birthday_day: int, send_time: str, message: str, enabled: str | None) -> None:
    date(2000, birthday_month, birthday_day)
    datetime.strptime(send_time, "%H:%M")
    birthday.name = name.strip()
    birthday.telegram_recipient = telegram_recipient.strip()
    birthday.birthday_month = birthday_month
    birthday.birthday_day = birthday_day
    birthday.send_time = send_time
    birthday.message = message.strip()
    birthday.enabled = enabled == "on"
    birthday.updated_at = utcnow()


@app.post("/birthdays")
def birthday_create(name: str = Form(...), telegram_recipient: str = Form(...),
                    birthday_month: int = Form(...), birthday_day: int = Form(...),
                    send_time: str = Form(...), message: str = Form(...),
                    enabled: str | None = Form(None), session: Session = Depends(get_session)):
    birthday = Birthday(name="", telegram_recipient="", birthday_month=1,
                        birthday_day=1, send_time="09:00", message="")
    apply_form(birthday, name, telegram_recipient, birthday_month, birthday_day,
               send_time, message, enabled)
    session.add(birthday)
    session.commit()
    return redirect("/birthdays", "Birthday added")


@app.post("/birthdays/{birthday_id}")
def birthday_update(birthday_id: int, name: str = Form(...), telegram_recipient: str = Form(...),
                    birthday_month: int = Form(...), birthday_day: int = Form(...),
                    send_time: str = Form(...), message: str = Form(...),
                    enabled: str | None = Form(None), session: Session = Depends(get_session)):
    birthday = session.get(Birthday, birthday_id)
    if not birthday:
        raise HTTPException(404)
    apply_form(birthday, name, telegram_recipient, birthday_month, birthday_day,
               send_time, message, enabled)
    session.add(birthday)
    session.commit()
    return redirect("/birthdays", "Birthday updated")


@app.post("/birthdays/{birthday_id}/delete")
def birthday_delete(birthday_id: int, session: Session = Depends(get_session)):
    birthday = session.get(Birthday, birthday_id)
    if birthday:
        session.delete(birthday)
        session.commit()
    return redirect("/birthdays", "Birthday deleted")


@app.post("/birthdays/{birthday_id}/toggle")
def birthday_toggle(birthday_id: int, session: Session = Depends(get_session)):
    birthday = session.get(Birthday, birthday_id)
    if not birthday:
        raise HTTPException(404)
    birthday.enabled = not birthday.enabled
    birthday.updated_at = utcnow()
    session.add(birthday)
    session.commit()
    return redirect("/birthdays")


@app.post("/birthdays/{birthday_id}/send")
async def birthday_send(birthday_id: int):
    success = await send_birthday(birthday_id)
    return redirect("/birthdays", "Message sent" if success else "Send failed; see history")


@app.post("/birthdays/{birthday_id}/test")
async def birthday_test(birthday_id: int):
    success = await send_birthday(birthday_id, recipient="me")
    return redirect("/birthdays", "Test sent to Saved Messages" if success else "Test failed")


@app.get("/history", response_class=HTMLResponse)
def history(request: Request, session: Session = Depends(get_session)):
    rows = session.exec(select(SendHistory).order_by(SendHistory.attempted_at.desc()).limit(200)).all()
    return templates.TemplateResponse(request, "history.html", {"history": rows})


@app.get("/api/status")
async def api_status():
    return {"telegram": await telegram.status(), "timezone": TIMEZONE}
