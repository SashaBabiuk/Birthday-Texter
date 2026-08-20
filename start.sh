#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

confirm() {
    local answer
    read -r -p "$1 [y/N]: " answer
    [[ "$answer" =~ ^[YyТт]$ ]]
}

as_root() {
    if (( EUID == 0 )); then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        echo "Помилка: для встановлення потрібен sudo або запуск від root."
        exit 1
    fi
}

install_system_dependencies() {
    if command -v pacman >/dev/null 2>&1; then
        as_root pacman -S --needed --noconfirm python python-pip docker docker-compose qrencode
    elif command -v apt-get >/dev/null 2>&1; then
        as_root apt-get update
        as_root apt-get install -y python3 python3-venv python3-pip docker.io docker-compose-v2 qrencode
    elif command -v dnf >/dev/null 2>&1; then
        as_root dnf install -y python3 python3-pip docker docker-compose-plugin qrencode
    else
        echo "Помилка: автоматичне встановлення підтримує pacman, apt-get або dnf."
        exit 1
    fi
}

missing_system=()
command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || missing_system+=("Python")
command -v docker >/dev/null 2>&1 || missing_system+=("Docker")
command -v qrencode >/dev/null 2>&1 || missing_system+=("qrencode")

if ((${#missing_system[@]})); then
    echo "Не знайдено: ${missing_system[*]}"
    if confirm "Встановити відсутні системні залежності?"; then
        install_system_dependencies
    else
        echo "Встановлення скасовано."
        exit 1
    fi
fi

PYTHON_BIN="$(command -v python3 || command -v python)"

if [[ ! -x .venv/bin/python ]]; then
    if confirm "Створити Python virtual environment .venv?"; then
        "$PYTHON_BIN" -m venv .venv
    else
        echo "Без .venv застосунок не може запуститися."
        exit 1
    fi
fi

if ! .venv/bin/python -c 'import apscheduler, fastapi, jinja2, multipart, sqlmodel, telethon, uvicorn, yaml' \
    >/dev/null 2>&1; then
    if confirm "Встановити Python-залежності з requirements.txt?"; then
        .venv/bin/pip install -r requirements.txt
    else
        echo "Без Python-залежностей застосунок не може запуститися."
        exit 1
    fi
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "Не знайдено Docker Compose plugin."
    if confirm "Встановити Docker Compose?"; then
        install_system_dependencies
    else
        exit 1
    fi
fi

if command -v systemctl >/dev/null 2>&1 && ! systemctl is-active --quiet docker; then
    if confirm "Служба Docker не запущена. Запустити її зараз?"; then
        as_root systemctl enable --now docker
    else
        exit 1
    fi
fi

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
    if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
        DOCKER=(sudo docker)
    else
        echo "Помилка: немає доступу до Docker daemon."
        echo "Додайте користувача до групи docker або запустіть скрипт через sudo."
        exit 1
    fi
fi

read -r -p "Telegram App ID: " TELEGRAM_APP_ID
read -r -s -p "Telegram API Hash: " TELEGRAM_APP_HASH
echo

if [[ ! "$TELEGRAM_APP_ID" =~ ^[0-9]+$ ]]; then
    echo "Помилка: App ID має складатися лише з цифр."
    exit 1
fi

if [[ ! "$TELEGRAM_APP_HASH" =~ ^[[:xdigit:]]{32}$ ]]; then
    echo "Помилка: API Hash має містити 32 шістнадцяткові символи."
    exit 1
fi

echo "Зупиняю поточний контейнер..."
"${DOCKER[@]}" compose down

if [[ -z "$("${DOCKER[@]}" compose images -q birthday-texter 2>/dev/null)" ]]; then
    if confirm "Docker image ще не створений. Зібрати його зараз?"; then
        "${DOCKER[@]}" compose build
    else
        exit 1
    fi
fi

mkdir -p data
echo "Виправляю права доступу до persistent data..."
"${DOCKER[@]}" compose run --rm --no-deps --entrypoint chown birthday-texter \
    -R "$(id -u):$(id -g)" /app/data

umask 077
printf '[Telegram]\napi_id = %s\napi_hash = %s\n' \
    "$TELEGRAM_APP_ID" "$TELEGRAM_APP_HASH" > config.ini

export TELEGRAM_API_ID="$TELEGRAM_APP_ID"
export TELEGRAM_API_HASH="$TELEGRAM_APP_HASH"

echo "Перевіряю Telegram session..."
.venv/bin/python -c '
import asyncio
import getpass
import os
import subprocess
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

def show_qr(url):
    subprocess.run(["qrencode", "-t", "ANSIUTF8", url], check=True)

async def authorize():
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    client = TelegramClient("data/telegram", api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            print("Session не авторизована. Увійдіть без SMS через QR-код.")
            print("Telegram → Налаштування → Пристрої → Підключити пристрій.")
            qr_login = await client.qr_login()
            while True:
                show_qr(qr_login.url)
                try:
                    await qr_login.wait(timeout=60)
                    break
                except asyncio.TimeoutError:
                    print("QR-код застарів, створюю новий...")
                    await qr_login.recreate()
                except SessionPasswordNeededError:
                    password = getpass.getpass("Пароль Telegram 2FA: ")
                    await client.sign_in(password=password)
                    break
        me = await client.get_me()
        account = f"@{me.username}" if me.username else (me.first_name or str(me.id))
        print(f"Telegram підключено як {account}")
    finally:
        await client.disconnect()

asyncio.run(authorize())
'

echo "Запускаю Birthday Texter..."
"${DOCKER[@]}" compose up --build -d
"${DOCKER[@]}" compose ps
echo "Готово: http://localhost:8080"
