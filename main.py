"""This module serves as the main entry point for the Telegram bot application.

It handles the initialization of the bot, sets up scheduled tasks for sending messages and media,
and manages user interactions. The module integrates with the worker functions to perform various
tasks such as sending greetings, media items, and reminders, while utilizing the APScheduler for
task scheduling.
"""

import asyncio
import logging
import logging.config
from configparser import ConfigParser, ExtendedInterpolation

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message

from src import worker

logging.config.fileConfig("logging.conf")

# Hidding non-critical logs from other modules
logging.getLogger("telethon").setLevel(logging.CRITICAL)
logging.getLogger("apscheduler").setLevel(logging.CRITICAL)

logging.info("User bot is connecting...")

logging.debug("Trying to read the configuration file...")
config = ConfigParser(interpolation=ExtendedInterpolation())
config.read("config.ini")
logging.debug("The configuration file was read successfully.")

logging.debug("Trying to connect the user bot client to Telegram...")
client = TelegramClient(
    "src/data/bot", config.get("Telegram", "api_id"), config.get("Telegram", "api_hash")
).start()
logging.debug("User bot client connected to Telegram successfully.")
logging.info("User bot connected!")


@client.on(events.NewMessage("me", pattern="/health"))
async def handle_health(event: Message | events.NewMessage):
    """Handles the /health command and responds with the application's health status.

    This asynchronous function listens for messages containing the /health command and replies with
    the current health status of the application. It provides a simple way for users to check if the
    bot is operational.

    Args:
        event (Message | events.NewMessage): The event object representing the incoming message.

    Raises:
        Exception: If there is an error while sending the reply.
    """
    logging.debug("Running method `handle_health`...")
    try:
        health_status = worker.health()
        logging.info("Sending health status response: %s", health_status)
        await event.reply(health_status)
        logging.info("Health status sent successfully.")

    except Exception as e:
        logging.error("Error while sending health status response: %s | event = %s", e, event)
        raise e

    logging.debug("Method `handle_health` finished.")


@client.on(events.NewMessage("me", pattern="/greeting_info"))
async def handle_greeting_info(event: Message | events.NewMessage):
    """Handles the /greeting_info command and responds with the next greeting time.

    This asynchronous function listens for messages containing the /greeting_info command and
    replies with the scheduled time for the next greeting. It provides users with information about
    when they can expect the next greeting message.

    Args:
        event (Message | events.NewMessage): The event object representing the incoming message.

    Raises:
        Exception: If there is an error while sending the reply.
    """
    logging.debug("Running method `handle_greeting_info`...")
    try:
        next_greeting_time = worker.next_greeting_time
        logging.info("Next greeting time retrieved: %s", next_greeting_time)

        await event.reply(f"Next greeting at {next_greeting_time}")
        logging.info("Greeting info sent successfully.")

    except Exception as e:
        logging.error("Error while sending greeting info response: %s | event = %s", e, event)
        raise e

    logging.debug("Method `handle_greeting_info` finished.")


@client.on(events.NewMessage("me", pattern="/send_greeting"))
async def handle_send_greeting(event: Message | events.NewMessage):
    """Handles the /send_greeting command to send a morning greeting.

    This asynchronous function listens for messages containing the /send_greeting command and
    triggers the sending of a morning greeting via the Telegram client. It then replies to the user
    to confirm that the action has been completed.

    Args:
        event (Message | events.NewMessage): The event object representing the incoming message.

    Raises:
        Exception: If there is an error while sending the greeting or the reply.
    """
    logging.debug("Running method `handle_send_greeting`...")
    try:
        logging.info("Triggering the sending of the morning greeting...")
        await worker.send_morning_greeting(client)
        logging.info("Morning greeting sent successfully.")

        await event.reply("Done!")
        logging.info("Confirmation reply sent to user.")

    except Exception as e:
        logging.error("Error while sending morning greeting or reply: %s | event = %s", e, event)
        raise e

    logging.debug("Method `handle_send_greeting` finished.")


@client.on(events.NewMessage("me", pattern="/test_greeting"))
async def handle_test_greeting(event: Message | events.NewMessage):
    """Handles the /test_greeting command to send a test morning greeting.

    This asynchronous function listens for messages containing the /test_greeting command and
    triggers the sending of a morning greeting via the Telegram client without marking it as used.
    It then replies to the user to confirm that the action has been completed.

    Args:
        event (Message | events.NewMessage): The event object representing the incoming message.

    Raises:
        Exception: If there is an error while sending the greeting or the reply.
    """
    logging.debug("Running method `handle_test_greeting`...")
    try:
        logging.info("Triggering the sending of a test morning greeting...")
        await worker.send_morning_greeting(client, user_id="me", set_as_used=False)
        logging.info("Test morning greeting sent successfully.")

        await event.reply("Done!")
        logging.info("Confirmation reply sent to user.")

    except Exception as e:
        logging.error(
            "Error while sending test morning greeting or reply: %s | event = %s", e, event
        )
        raise e

    logging.debug("Method `handle_test_greeting` finished.")


@client.on(events.NewMessage("me", pattern="/afternoon_media_info"))
async def handle_afternoon_media(event: Message | events.NewMessage):
    """Handles the /afternoon_media_info command and responds with the next media time.

    This asynchronous function listens for messages containing the /afternoon_media_info command
    and replies with the scheduled time for the next afternoon media. It provides users with
    information about when they can expect the next media item.

    Args:
        event (Message | events.NewMessage): The event object representing the incoming message.

    Raises:
        Exception: If there is an error while sending the reply.
    """
    logging.debug("Running method `handle_afternoon_media`...")
    try:
        next_afternoon_media_time = worker.next_afternoon_media_time
        logging.info("Next afternoon media time retrieved: %s", next_afternoon_media_time)

        await event.reply(f"Next media at {next_afternoon_media_time}")
        logging.info("Afternoon media info sent successfully.")

    except Exception as e:
        logging.error(
            "Error while sending afternoon media info response: %s | event = %s", e, event
        )
        raise e

    logging.debug("Method `handle_afternoon_media` finished.")


@client.on(events.NewMessage("me", pattern="/send_afternoon_media"))
async def handle_send_afternoon_media(event: Message | events.NewMessage):
    """Handles the /send_afternoon_media command to send an afternoon media item.

    This asynchronous function listens for messages containing the /send_afternoon_media command
    and triggers the sending of an afternoon media item via the Telegram client. It then replies to
    the user to confirm that the action has been completed.

    Args:
        event (Message | events.NewMessage): The event object representing the incoming message.

    Raises:
        Exception: If there is an error while sending the media or the reply.
    """
    logging.debug("Running method `handle_send_afternoon_media`...")
    try:
        logging.info("Triggering the sending of the afternoon media item...")
        await worker.send_afternoon_media(client)
        logging.info("Afternoon media sent successfully.")

        await event.reply("Done!")
        logging.info("Confirmation reply sent to user.")

    except Exception as e:
        logging.error("Error while sending afternoon media or reply: %s | event = %s", e, event)
        raise e

    logging.debug("Method `handle_send_afternoon_media` finished.")


@client.on(events.NewMessage("me", pattern="/test_afternoon_media"))
async def handle_test_afternoon_media(event: Message | events.NewMessage):
    """Handles the /test_afternoon_media command to send a test afternoon media item.

    This asynchronous function listens for messages containing the /test_afternoon_media command
    and triggers the sending of an afternoon media item via the Telegram client without marking it
    as used. It then replies to the user to confirm that the action has been completed.

    Args:
        event (Message | events.NewMessage): The event object representing the incoming message.

    Raises:
        Exception: If there is an error while sending the media or the reply.
    """
    logging.debug("Running method `handle_test_afternoon_media`...")
    try:
        logging.info("Triggering the sending of a test afternoon media item...")
        await worker.send_afternoon_media(client, user_id="me", set_as_used=False)
        logging.info("Test afternoon media sent successfully.")

        await event.reply("Done!")
        logging.info("Confirmation reply sent to user.")

    except Exception as e:
        logging.error(
            "Error while sending test afternoon media or reply: %ss | event = %s", e, event
        )
        raise e

    logging.debug("Method `handle_test_afternoon_media` finished.")


@client.on(events.NewMessage("me", pattern="/stats"))
async def handle_stats(event: Message | events.NewMessage):
    """Handles the /stats command to send statistics to the user.

    This asynchronous function listens for messages containing the /stats command and triggers the
    sending of statistics related to the application via the Telegram client. It provides users with
    insights into the current state of the application.

    Args:
        event (Message | events.NewMessage): The event object representing the incoming message.

    Raises:
        Exception: If there is an error while sending the statistics.
    """
    logging.debug("Running method `handle_stats`...")
    try:
        logging.info("Triggering the sending of application statistics...")
        await worker.send_stats(client, user_id="me")
        logging.info("Statistics sent successfully.")

    except Exception as e:
        logging.error("Error while sending statistics: %ss | event = %s", e, event)
        raise e

    logging.debug("Method `handle_stats` finished.")


async def main():
    """Main entry point for starting the Telegram bot and scheduling tasks.

    This asynchronous function initializes the scheduler and starts the various tasks for sending
    morning greetings, afternoon media, and pill reminders. It then enters an infinite loop to keep
    the application running and responsive.
    """
    logging.info("Starting the scheduler...")
    logging.debug("Initializing the scheduler...")
    scheduler = AsyncIOScheduler()
    logging.debug("Scheduler initialized successfully.")

    logging.debug("Scheduling morning greeting task...")
    worker.start_sending_morning_greeting(scheduler, client, try_today=True)
    logging.debug("Morning greeting task scheduled successfully.")

    logging.debug("Scheduling afternoon media task...")
    worker.start_sending_afternoon_media(scheduler, client, try_today=True)
    logging.debug("Afternoon media task scheduled successfully.")

    logging.debug("Scheduling pill reminder task...")
    worker.start_sending_pills_reminder(scheduler, client)
    logging.debug("Pill reminder task scheduled successfully.")

    logging.debug("Setting up handler to stop pill reminders for today...")
    worker.handle_stop_sending_pill_reminder_for_today(client)
    logging.debug("Handler to stop pill reminders for today set up successfully.")

    logging.debug("Starting the scheduler...")
    scheduler.start()
    logging.debug("Scheduler started successfully.")

    logging.info("User bot is now running!")
    while True:
        await asyncio.sleep(1)


client.loop.run_until_complete(main())
