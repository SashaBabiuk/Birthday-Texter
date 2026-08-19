# Birthday Texter

Birthday Texter is a self-hosted web application that sends recurring birthday messages from your
personal Telegram account.

Birthdays are managed through a local web interface and stored in SQLite. APScheduler checks for
due messages every minute, and Telethon sends each greeting as a normal Telegram message. The app
does not create Telegram Scheduled Messages.

## Features

- Dashboard with upcoming birthdays and Telegram connection status
- Add, edit, delete, enable, and disable birthday entries
- Yearly recurring birthday messages
- Persistent duplicate protection using `last_sent_year`
- Automatic retries after failed sends
- Manual **Send now** action
- Safe **Test** action that sends to Telegram Saved Messages
- Send history with errors and delivery results
- SQLite database and Telegram session stored in `data/`
- Single-container Docker deployment

## How sending works

A birthday is due when all of the following are true:

- The entry is enabled.
- Its month and day match the current date in `Europe/Kyiv`.
- Its configured send time has passed.
- It has not already been sent successfully during the current year.

If the server starts after the scheduled time, the message is sent on the next dispatcher run.
`last_sent_year` is updated only after Telegram confirms the send. Failed attempts are recorded in
the history and remain eligible for a later retry.

Manual **Send now** and **Test** actions do not mark the birthday as sent for the year.

## Architecture

```text
Jinja2 + HTMX web UI
        ↓
FastAPI → SQLite/SQLModel
        ↓
APScheduler birthday dispatcher
        ↓
Telethon → Telegram
```

The legacy greeting, media, and pill-reminder code remains in the repository but is not started by
the Birthday Texter web container.

## Requirements

- Python 3.11 or newer, or Docker with Docker Compose
- Telegram API ID and API hash from <https://my.telegram.org>
- An authorized Telethon session

## Existing Telegram session

The original application stores its session at `src/data/bot.session`. On the first local startup,
Birthday Texter copies it to `data/telegram.session`. The original file is left untouched. Both
session paths and the entire `data/` directory are excluded from Git and the Docker build context.

If the automatic copy has not run before using Docker, copy the session manually:

```bash
mkdir -p data
cp src/data/bot.session data/telegram.session
```

## Run locally

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Provide Telegram credentials:

```bash
export TELEGRAM_API_ID='your_api_id'
export TELEGRAM_API_HASH='your_api_hash'
```

The local application can alternatively read credentials from the existing ignored `config.ini`:

```ini
[Telegram]
api_id = your_api_id
api_hash = your_api_hash
```

Start the web application:

```bash
.venv/bin/uvicorn birthday_texter.app:app \
  --host 127.0.0.1 \
  --port 8080
```

Open <http://127.0.0.1:8080>.

## Run with Docker Compose

Ensure `data/telegram.session` exists, then run:

```bash
export TELEGRAM_API_ID='your_api_id'
export TELEGRAM_API_HASH='your_api_hash'
docker compose up --build -d
```

Open <http://localhost:8080>.

View logs or stop the application:

```bash
docker compose logs -f birthday-texter
docker compose down
```

The Compose volume maps the host `data/` directory to `/app/data`, so the database and Telegram
session survive container replacement and upgrades.

## Using the web UI

1. Open the dashboard and confirm that Telegram is connected.
2. Select **Birthdays**, then **Add birthday**.
3. Enter a display name, Telegram recipient, month, day, Kyiv send time, and message.
4. Save the entry. No application restart is required.
5. Use **Test** to send the message to Saved Messages.
6. Check **History** for the result.

A Telegram recipient can be an `@username` or a numeric user/chat ID. **Send now** sends immediately
to that recipient, so use **Test** when validating a message or recipient setup.

## Persistent data

```text
data/
├── birthday_texter.db
└── telegram.session
```

The SQLite database contains:

- `birthdays` — birthday definitions and yearly send state
- `send_history` — successful and failed attempts
- `settings` — application settings for later configuration phases

Back up the complete `data/` directory while the application is stopped.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `TELEGRAM_API_ID` | Value from `config.ini` | Telegram application API ID |
| `TELEGRAM_API_HASH` | Value from `config.ini` | Telegram application API hash |
| `TZ` | `Europe/Kyiv` | Scheduler and birthday timezone |
| `SCHEDULER_INTERVAL` | `60` | Dispatcher interval in seconds |
| `DATA_DIR` | `./data` locally, `/app/data` in Docker | Persistent storage directory |

The Docker image deliberately runs one Uvicorn worker. Do not start multiple application instances
against the same data directory because each instance would run its own scheduler.

## Development checks

```bash
.venv/bin/python -m compileall -q birthday_texter main.py src
docker build -f dockerfile -t birthday-texter:phase1 .
```

## Security

Birthday Texter controls a personal Telegram account. Keep these files private:

- `config.ini`
- `data/telegram.session`
- `src/data/bot.session`
- `data/birthday_texter.db`

The local command binds to `127.0.0.1`. Docker publishes port 8080 on the host; only use it on a
trusted network. Do not expose the application directly to the public internet without
authentication and HTTPS. For remote access, prefer a VPN or Tailscale.

## Legacy application

The original Telegram Auto Texter entry point remains available as `main.py` and continues to use
the legacy YAML files under `src/data/`. Birthday Texter does not modify or schedule those legacy
features.

## License

This project is licensed under the MIT License. See [license](license).
