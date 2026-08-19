# Birthday Texter — Product Specification

## Overview

Birthday Texter is a self-hosted web application that automatically sends recurring birthday messages from a personal Telegram account.

The user manages birthdays through a web interface instead of editing YAML or code.

The system is designed to work continuously for years with minimal maintenance.

Core flow:

`Web UI → Database → Scheduler → Telethon → Telegram`

The application sends a normal Telegram message from the authenticated personal account when a birthday becomes due.

It must not rely on Telegram Scheduled Messages created months or years in advance.

---

## Primary user experience

The user opens a local website, for example:

`http://localhost:8080`

or on a home server:

`http://192.168.1.50:8080`

The main page shows a table of birthday automations.

Example:

| Name   | Telegram | Birthday | Time  | Message                       | Enabled | Last sent | Actions         |
| ------ | -------- | -------- | ----- | ----------------------------- | ------- | --------- | --------------- |
| Andriy | @andriy  | Sep 14   | 10:00 | Андрій, з днем народження! 🎉 | Yes     | 2026      | Edit / Send now |
| Max    | @max     | Nov 03   | 12:00 | Макс, вітаю! 🥳               | Yes     | 2025      | Edit / Send now |

The user should never need to edit application files manually.

---

## Main UI

### Dashboard

The dashboard should show:

* total number of birthday entries
* birthdays today
* birthdays this week
* next scheduled birthday
* recent sends
* failed sends
* Telegram connection status

Example:

```text
Telegram: Connected as @myaccount

Today: 2 birthdays
This week: 5 birthdays
Total contacts: 83

Next:
Andriy
14 September, 10:00
```

---

## Birthdays page

Main management page.

Columns:

* Name
* Telegram recipient
* Birthday
* Send time
* Message preview
* Enabled
* Last sent
* Status
* Actions

Actions:

* Add birthday
* Edit
* Delete
* Enable / Disable
* Send now
* Test
* Duplicate entry

Search should work by:

* name
* Telegram username

Sorting should support:

* next birthday
* name
* last sent
* enabled/disabled

---

## Add / Edit birthday form

The form should contain:

### Name

Example:

`Andriy`

Used only for internal display.

### Telegram recipient

Supported values:

`@username`

or a Telegram numeric user/chat ID.

Later the UI may include a Telegram contact picker.

### Birthday

User chooses:

* month
* day

The year is not required.

Example:

`14 September`

Stored internally as:

`09-14`

### Send time

Example:

`10:00`

Timezone:

`Europe/Kyiv`

### Message

Multiline text field.

Example:

`Андрій, з днем народження! 🎉 Бажаю всього найкращого!`

Telegram formatting may eventually support:

* bold
* italic
* links
* emoji

### Enabled

Toggle:

`ON / OFF`

### Save

When saved, the entry immediately becomes part of the birthday scheduler.

No restart should be required.

---

## Recurrence

Every birthday entry repeats automatically every year.

The user should not have to create a new schedule every year.

Example:

```text
Andriy
Birthday: September 14
Time: 10:00

2026 → sent
2027 → automatically sent
2028 → automatically sent
...
```

The record remains active until disabled or deleted.

---

## Sending behavior

The application checks for due messages periodically.

Recommended interval:

`1 minute`

A birthday is due when:

* the record is enabled
* today's month/day equals the configured birthday
* configured send time has passed
* the message has not already been successfully sent during the current year

Example:

Configured:

`10:00`

Server was offline:

`09:45 → 10:17`

Server starts:

`10:17`

Expected behavior:

send immediately at `10:17`.

The birthday must not be permanently missed just because the server was down at the exact scheduled minute.

---

## Duplicate protection

Duplicate messages must be prevented.

Each birthday record should store persistent state such as:

`last_sent_year`

Example:

```text
last_sent_year = 2026
```

The system must only update this value after Telegram confirms successful delivery of the send request.

If sending fails:

* do not update `last_sent_year`
* record the failure
* retry later

A Docker restart must not cause duplicate birthday messages.

---

## Send history

The application should maintain an event log.

Example:

| Date             | Person | Telegram | Result |
| ---------------- | ------ | -------- | ------ |
| 2026-09-14 10:00 | Andriy | @andriy  | Sent   |
| 2026-09-16 11:03 | Max    | @max     | Failed |

Each record should contain:

* birthday entry ID
* attempted time
* result
* Telegram recipient
* message
* error message if failed

This provides an audit trail.

---

## Send now

Each birthday should have:

`Send now`

This immediately sends the configured message through Telegram.

Useful for:

* testing
* manually triggering a greeting
* confirming that the Telegram recipient is correct

This action must not automatically update the yearly birthday state unless explicitly intended.

A separate option may be:

`Send now and mark as sent this year`

---

## Test mode

The application should support a safe test destination.

For example:

`Send test to Saved Messages`

This sends the birthday message to:

`me`

instead of the actual recipient.

This allows testing message formatting without bothering another person.

---

## Telegram connection page

A Settings page should show Telegram session information.

Example:

```text
Telegram account
Status: Connected
Account: @myusername
Phone: +380••••••••
Session: Active
```

Actions:

* Test connection
* Reconnect
* Log out
* Send test to Saved Messages

Credentials such as API hash must never be displayed after initial configuration.

---

## Telegram authentication

The application uses:

* Telegram API ID
* Telegram API hash
* Telethon
* personal Telegram account session

The Telegram session should be stored persistently on the host.

Example:

`data/telegram.session`

This file must never be downloadable through the web UI.

It must never be committed to Git.

---

## Settings page

Settings should contain:

### General

Timezone:

`Europe/Kyiv`

Scheduler interval:

`60 seconds`

### Telegram

API ID

API Hash

Connection status

### Notifications

Optional notification to Saved Messages if:

* a birthday send fails
* Telegram disconnects
* scheduler encounters an error

Example:

`Birthday Texter failed to send message to @andriy.`

---

## Database

For the web application version, use SQLite instead of YAML.

Recommended:

`data/birthday_texter.db`

SQLite is sufficient because this is a single-user application with relatively low traffic.

Suggested tables:

### birthdays

```text
id
name
telegram_recipient
birthday_month
birthday_day
send_time
message
enabled
last_sent_year
created_at
updated_at
```

### send_history

```text
id
birthday_id
attempted_at
recipient
message
status
error
```

### settings

```text
key
value
```

---

## Backend

Recommended stack:

* Python
* FastAPI
* Telethon
* APScheduler
* SQLite
* SQLAlchemy or SQLModel

FastAPI is suitable because the existing project is already Python-based and the Telegram worker is Python.

The backend should expose endpoints such as:

```text
GET    /api/birthdays
POST   /api/birthdays
PUT    /api/birthdays/{id}
DELETE /api/birthdays/{id}

POST   /api/birthdays/{id}/send
POST   /api/birthdays/{id}/test

GET    /api/history
GET    /api/status
GET    /api/settings
PUT    /api/settings
```

---

## Frontend

For the first version, avoid unnecessary complexity.

Recommended options:

### Preferred

FastAPI + server-rendered HTML using Jinja2 + HTMX.

Advantages:

* one application
* minimal JavaScript
* easy Docker deployment
* simple maintenance
* no Node.js build pipeline required

This is probably the best architecture for this project.

### Alternative

React/Vue frontend + FastAPI API.

Use this only if the interface becomes substantially more complex later.

---

## Suggested UI stack

Recommended:

* FastAPI
* Jinja2
* HTMX
* simple CSS framework such as Pico CSS or Bootstrap

This gives a modern responsive UI without turning the application into a large frontend project.

---

## Docker

The whole application should run as one Docker container initially.

Example architecture:

```text
Docker container
│
├── FastAPI web server
├── APScheduler
├── Telethon client
└── SQLite
```

Persistent Docker volume:

```text
/app/data
```

Containing:

```text
birthday_texter.db
telegram.session
```

Environment:

```text
TZ=Europe/Kyiv
```

Potential Docker Compose:

```yaml
services:
  birthday-texter:
    build: .
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      TZ: Europe/Kyiv
    volumes:
      - ./data:/app/data
```

---

## Security

This application controls a personal Telegram account, therefore security matters.

By default the web UI should bind only to:

`127.0.0.1`

or the trusted local network.

Do not expose the service directly to the public internet without authentication and HTTPS.

If remote access is needed, preferable solutions include:

* Tailscale
* VPN
* reverse proxy with authentication

Telegram session files must never be exposed through static file routes.

---

## Desired finished product

The final application experience should be:

1. Open Birthday Texter.
2. Log into Telegram once.
3. Click `Add birthday`.
4. Enter:

```text
Name: Andriy
Telegram: @andriy
Birthday: September 14
Time: 10:00
Message: Андрій, з днем народження! 🎉
```

5. Click `Save`.
6. Forget about it.

Every year:

```text
September 14, 10:00
↓
Birthday Texter detects the due entry
↓
Telethon sends a normal Telegram message
↓
Andriy receives the message from the user's personal account
↓
Birthday Texter records the successful send
↓
The same entry becomes eligible again next year
```

No manual reminders.

No yearly reconfiguration.

No Telegram Scheduled Messages created in advance.

No third-party automation provider holding the Telegram session.

## Development priority

Implement in this order:

1. Replace birthday YAML with SQLite.
2. Create database models.
3. Implement reliable birthday dispatcher.
4. Preserve existing Telethon session.
5. Add FastAPI.
6. Build birthdays list page.
7. Add create/edit/delete forms.
8. Add `Send now`.
9. Add `Test to Saved Messages`.
10. Add send history.
11. Add Telegram status page.
12. Add Docker Compose.
13. Remove unused original greeting/media/pill functionality.
14. Harden security.
15. Add backup/export functionality.
