"""This module provides functionality for sending scheduled messages and media via Telegram.

It includes functions for sending morning greetings and afternoon messages, media items, and
reminders, as well as managing the state of sent items. The module utilizes YAML files for
configuration and data storage, and it integrates with the APScheduler for scheduling tasks.
"""

import asyncio
import bisect
import logging
import logging.config
import random
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message
from telethon.tl.types import InputDocument

from src.sentence_generator import morning
from src.utils.random import random_time

logging.config.fileConfig("logging.conf")

DATA_PATH = Path("src/data")
MEDIA_PATH = DATA_PATH / "media"
MEDIA_YAML_PATH = DATA_PATH / "media.yaml"
REGISTER_YAML_PATH = DATA_PATH / "register.yaml"
STICKERS_YAML_PATH = DATA_PATH / "stickers.yaml"
TELEGRAM_CONFIG_PATH = DATA_PATH / "telegram_config.yaml"

next_greeting_time: datetime = datetime.now()
next_afternoon_media_time: datetime = datetime.now()
keep_sending_pill_reminder = False


class CustomYamlDumper(yaml.Dumper):
    """Custom YAML dumper that modifies the indentation behavior.

    This class extends the default YAML dumper to ensure that the indentation is always increased
    for block styles, making the output more readable and consistent. It overrides the
    `increase_indent` method to customize the indentation settings.
    """

    def increase_indent(self, flow: bool = False, *args, **kwargs):
        """Increase the indentation level for YAML output.

        This method modifies the behavior of indentation to ensure that it is not indentless,
        providing a clearer structure in the generated YAML.

        Args:
            flow (bool, optional): Indicates whether the indentation is for flow style. Defaults to
                False.
        """
        return super().increase_indent(flow=flow, indentless=False)


def read_yaml(path: Path, *, encoding: str = "utf-8") -> dict:
    """Reads a YAML file and returns its contents as a dictionary.

    This function loads the specified YAML file from the given path and parses its content into
    a Python dictionary, allowing for easy access to configuration settings.

    Args:
        path (Path): The path to the YAML file to be read.
        encoding (str, optional): The character encoding to use when reading the file. Defaults to
            "utf-8".

    Returns:
        dict: A dictionary containing the contents of the YAML file.

    Raises:
        FileNotFoundError: If the specified YAML file does not exist.
        yaml.YAMLError: If there is an error parsing the YAML file.
    """
    logging.debug("Running method `read_yaml`...")
    try:
        with open(path, encoding=encoding) as f:
            data = yaml.safe_load(f)
            logging.info("YAML file read successfully.")
            return data

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", path)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file at %s: %s", path, e)
        raise e

    except Exception as e:
        logging.error("Error while reading YAML file at %s: %s", path, e)
        raise e

    logging.debug("Method `read_yaml` finished.")


def save_yaml(data: dict, path: Path, *, encoding: str = "utf-8"):
    """Saves a Python dictionary as a YAML file.

    This function serializes the provided dictionary and writes it to the specified file path
    in YAML format, allowing for easy storage and retrieval of structured data.

    Args:
        data (dict): The Python object to be saved as YAML.
        path (Path): The path to the YAML file where the data will be saved.
        encoding (str, optional): The character encoding to use when writing the file. Defaults to
            "utf-8".
    """
    logging.debug("Running method `save_yaml`...")
    try:
        with open(path, "w", encoding=encoding) as f:
            yaml.dump(data, f, Dumper=CustomYamlDumper)
            logging.info("Data saved successfully to %s", path)

    except Exception as e:
        logging.error("Error while saving data to YAML file at %s: %s", path, e)
        raise e

    logging.debug("Method `save_yaml` finished.")


def filter_by_register(data: dict | list, register: list["int | str"], *, key: str = "uid") -> list:
    """Filters the data to exclude items present in the register.

    This function checks the provided data against a list of identifiers in the register and
    returns a new list containing only those items that are not in the register. It allows for
    flexible filtering based on a specified key.

    Args:
        data (dict | list): The data to be filtered, which can be a dictionary or a list.
        register (list[int | str]): A list of identifiers to filter out from the data.
        key (str, optional): The key used to identify items in the data for filtering. Defaults to
            "uid".

    Returns:
        list: A list of items from the data that are not present in the register.
    """
    logging.debug("Running method `filter_by_register`...")
    logging.info(
        "Starting filtering process with data %s, register %s and key %s.", data, register, key
    )
    _register = set(register)
    filtered_data = [d for d in data if (d if key is None else d[key]) not in _register]
    logging.debug("Method `filter_by_register` finished.")
    return filtered_data


def text_to_timedelta(text: str) -> timedelta:
    """Converts a text representation of time into a timedelta object.

    This function takes a string formatted as "HH:MM:SS" and converts it into a timedelta object,
    allowing for easy manipulation of time intervals in Python.

    Args:
        text (str): The text representation of time to be parsed.

    Returns:
        timedelta: A timedelta object representing the parsed time.

    Raises:
        ValueError: If the input string is not in the expected format or cannot be converted to
            integers.
    """
    logging.debug("Running method `text_to_timedelta`...")
    try:
        _time: list[int] = [int(x) for x in text.split(":")]
        if len(_time) != 3:
            logging.error("Input must be in the format 'HH:MM:SS'. Input: %s", text)
            raise ValueError("Input must be in the format 'HH:MM:SS'")

        result = timedelta(hours=_time[0], minutes=_time[1], seconds=_time[2])
        logging.info("Conversion successful: %s", result)
        return result

    except ValueError as e:
        logging.error("Error converting text to timedelta: %s", e)
        raise e

    logging.debug("Method `text_to_timedelta` finished.")


def get_next_time(tm: timedelta, timespan: timedelta, try_now: bool = False) -> datetime:
    """Calculates the next occurrence of a specified time based on the current time.

    This function determines the next datetime by adding a specified time duration to the current
    time and adjusting it according to the provided time interval. It can optionally consider the
    current time as a starting point for the calculation.

    Args:
        tm (timedelta): The time of day to calculate the next occurrence for.
        timespan (timedelta): The interval to add if the calculated time is in the past.
        try_now (bool, optional): If True, the current time is used as the starting point;
            otherwise, the timespan is added to the current time. Defaults to False.

    Returns:
        datetime: The next occurrence of the specified time as a datetime object.
    """
    logging.debug("Running method `get_next_time`...")
    logging.info(
        "Calculating next time with tm: %s, timespan: %s, try_now: %s", tm, timespan, try_now
    )
    now = datetime.now()
    if not try_now:
        now += timespan

    dt = datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=tm.seconds // 3600,
        minute=(tm.seconds % 3600) // 60,
        second=tm.seconds % 60,
    )

    logging.debug("Calculated datetime before adjustment: %s", dt)

    if dt < datetime.now():
        logging.debug("Calculated time is in the past. Adding timespan: %s", timespan)
        dt += timespan

    logging.info("Next occurrence of time is: %s", dt)
    logging.debug("Method `get_next_time` finished.")
    return dt


def health() -> str:
    """Returns the health status of the application.

    This function provides a simple check to indicate that the application is running and
    operational. It returns a string message confirming the application's status.

    Returns:
        str: A message indicating that the application is alive.
    """
    logging.debug("Running method `health`...")
    status = "Alive"
    logging.info("Application health status: %s", status)
    logging.debug("Method `health` finished.")
    return status


def get_morning_greeting() -> str:
    """Retrieves a morning greeting message.

    This function acts as a wrapper to obtain a good morning greeting from the `morning` module. It
    provides a simple interface to access the greeting functionality.

    Returns:
        str: A morning greeting message.
    """
    logging.debug("Running method `get_morning_greeting`...")
    logging.info("Retrieving morning greeting message...")
    greeting = morning.get_morning_greeting()
    logging.info("Morning greeting retrieved: %s", greeting)
    logging.debug("Method `get_morning_greeting` finished.")
    return greeting


def get_morning_sticker() -> dict:
    """Retrieves a random morning sticker that has not been sent yet.

    This function reads the list of morning stickers from a YAML file and filters out those that
    have already been sent. It then randomly selects one of the remaining stickers and prepares it
    for use by encoding its file reference.

    Returns:
        dict: A dictionary representing the selected morning sticker, including its file reference
            and other associated data.

    Raises:
        FileNotFoundError: If the specified YAML files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML files.
        ValueError: If there are no available morning stickers to choose from.
    """
    logging.debug("Running method `get_morning_sticker`...")
    try:
        logging.info("Retrieving morning stickers...")
        morning_stickers_sent: list = read_yaml(REGISTER_YAML_PATH).get("morning_stickers", [])
        logging.debug("Sent morning stickers: %s", morning_stickers_sent)

        morning_stickers: list = filter_by_register(
            data=read_yaml(STICKERS_YAML_PATH, encoding="latin-1")["morning_stickers"],
            register=morning_stickers_sent,
        )
        logging.debug("Available morning stickers after filtering: %d", len(morning_stickers))

        if not morning_stickers:
            logging.error("No available morning stickers to choose from.")
            raise ValueError("No available morning stickers to choose from.")

        morning_sticker: dict = random.choice(morning_stickers)
        morning_sticker["file_reference"] = morning_sticker["file_reference"].encode("latin-1")
        logging.info("Selected morning sticker: %s", morning_sticker)
        logging.debug("Method `get_morning_sticker` finished.")
        return morning_sticker

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", e)
        raise e


def get_morning_media() -> dict:
    """Retrieves a random morning media item that has not been sent yet.

    This function reads the list of morning media items from a YAML file and filters out those that
    have already been sent. It then randomly selects one of the remaining media items for use.

    Returns:
        dict: A dictionary representing the selected morning media item, including its associated
            data.

    Raises:
        FileNotFoundError: If the specified YAML files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML files.
        ValueError: If there are no available morning media items to choose from.
    """
    logging.debug("Running method `get_morning_media`...")
    try:
        logging.info("Retrieving morning media items...")
        morning_media_sent = read_yaml(REGISTER_YAML_PATH).get("morning_media", [])
        logging.debug("Sent morning media items: %s", morning_media_sent)

        morning_media = filter_by_register(
            data=read_yaml(MEDIA_YAML_PATH)["morning_media"],
            register=morning_media_sent,
        )
        logging.debug("Available morning media items after filtering: %d", len(morning_media))

        if not morning_media:
            logging.error("No available morning media items to choose from.")
            raise ValueError("No available morning media items to choose from.")

        selected_media = random.choice(morning_media)
        logging.info("Selected morning media item: %s", selected_media)
        logging.debug("Method `get_morning_media` finished.")
        return selected_media

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", e)
        raise e


def get_afternoon_media() -> dict:
    """Retrieves a random afternoon media item that has not been sent yet.

    This function reads the list of afternoon media items from a YAML file and filters out those
    that have already been sent. It then randomly selects one of the remaining media items for use.

    Returns:
        dict: A dictionary representing the selected afternoon media item, including its associated
            data.

    Raises:
        FileNotFoundError: If the specified YAML files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML files.
        ValueError: If there are no available afternoon media items to choose from.
    """
    logging.debug("Running method `get_afternoon_media`...")
    try:
        logging.info("Retrieving afternoon media items...")
        afternoon_media_sent = read_yaml(REGISTER_YAML_PATH).get("afternoon_media", [])
        logging.debug("Sent afternoon media items: %s", afternoon_media_sent)

        afternoon_media = filter_by_register(
            data=read_yaml(MEDIA_YAML_PATH)["afternoon_media"],
            register=afternoon_media_sent,
        )
        logging.debug("Available afternoon media items after filtering: %d", len(afternoon_media))

        if not afternoon_media:
            logging.error("No available afternoon media items to choose from.")
            raise ValueError("No available afternoon media items to choose from.")

        selected_media = random.choice(afternoon_media)
        logging.info("Selected afternoon media item: %s", selected_media)
        logging.debug("Method `get_afternoon_media` finished.")
        return selected_media

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", e)
        raise e


def set_as_used(entry: str, uid: int, db_yaml: Path):
    """Marks a specified entry as used by adding a unique ID to the register.

    This function updates the register by adding the provided unique ID to the list of used IDs for
    the specified entry. If the number of used IDs matches the total entries in the database, it
    clears the list for that entry.

    Args:
        entry (str): The key in the register that corresponds to the entry being updated.
        uid (int): The unique ID to be marked as used.
        db_yaml (Path): The path to the YAML file containing the database entries.

    Raises:
        FileNotFoundError: If the specified YAML files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML files.
    """
    logging.debug("Running method `set_as_used`...")
    try:
        logging.info("Marking entry '%s' as used for UID: %d", entry, uid)
        register = read_yaml(REGISTER_YAML_PATH)
        logging.debug("Current register before update: %s", register)

        if uid not in register[entry]:
            bisect.insort(register[entry], uid)
            logging.info("UID %d added to register for entry '%s'.", uid, entry)

            data = read_yaml(db_yaml)
            if len(register[entry]) == len(data[entry]):
                register[entry] = []
                logging.info("All entries for '%s' have been used. Clearing the register.", entry)

            save_yaml(register, REGISTER_YAML_PATH)
            logging.info("Register updated and saved successfully.")

        else:
            logging.info("UID %d is already marked as used for entry '%s'.", uid, entry)

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", e)
        raise e

    logging.debug("Method `set_as_used` finished.")


def set_morning_sticker_as_used(uid: int):
    """Marks a morning sticker as used for a specified unique ID.

    This function updates the register to indicate that the morning sticker has been used by the
    provided unique ID. It calls the `set_as_used` function with the appropriate parameters to
    perform the update.

    Args:
        uid (int): The unique ID to be marked as having used the morning sticker.

    Raises:
        FileNotFoundError: If the specified YAML files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML files.
    """
    logging.debug("Running method `set_morning_sticker_as_used`...")
    try:
        logging.info("Marking morning sticker as used for UID: %d", uid)
        set_as_used("morning_stickers", uid, STICKERS_YAML_PATH)
        logging.info("Morning sticker marked as used for UID: %d", uid)

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", e)
        raise e

    logging.debug("Method `set_morning_sticker_as_used` finished.")


def set_morning_media_as_used(uid: int):
    """Marks a morning media item as used for a specified unique ID.

    This function updates the register to indicate that the morning media item has been used by the
    provided unique ID. It calls the `set_as_used` function with the appropriate parameters to
    perform the update.

    Args:
        uid (int): The unique ID to be marked as having used the morning media item.

    Raises:
        FileNotFoundError: If the specified YAML files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML files.
    """
    logging.debug("Running method `set_morning_media_as_used`...")
    try:
        logging.info("Marking morning media as used for UID: %d", uid)
        set_as_used("morning_media", uid, MEDIA_YAML_PATH)
        logging.info("Morning media marked as used for UID: %d", uid)

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", e)
        raise e

    logging.debug("Method `set_morning_media_as_used` finished.")


def set_afternoon_media_as_used(uid: int):
    """Marks an afternoon media item as used for a specified unique ID.

    This function updates the register to indicate that the afternoon media item has been used by
    the provided unique ID. It calls the `set_as_used` function with the appropriate parameters to
    perform the update.

    Args:
        uid (int): The unique ID to be marked as having used the afternoon media item.

    Raises:
        FileNotFoundError: If the specified YAML files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML files.
    """
    logging.debug("Running method `set_afternoon_media_as_used`...")
    try:
        logging.info("Marking afternoon media as used for UID: %d", uid)
        set_as_used("afternoon_media", uid, MEDIA_YAML_PATH)
        logging.info("Afternoon media marked as used for UID: %d", uid)

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", e)
        raise e

    logging.debug("Method `set_afternoon_media_as_used` finished.")


async def send_morning_greeting(
    client: TelegramClient, user_id: str = "nathy", set_as_used: bool = True
):
    """Sends a morning greeting message along with a sticker and media to a user.

    This asynchronous function retrieves a morning greeting message, a sticker, and media, then
    sends them to the specified user via a Telegram client. It can also mark the sticker and media
    as used if specified.

    Args:
        client (TelegramClient): The Telegram client used to send messages.
        user_id (str, optional): The identifier for the user to whom the greeting is sent. Defaults
            to "nathy".
        set_as_used (bool, optional): Indicates whether to mark the sticker and media as used after
            sending. Defaults to True.

    Raises:
        FileNotFoundError: If the configuration or media files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML configuration.
        Exception: If there is an error sending messages through the Telegram client.
    """
    logging.debug("Running method `send_morning_greeting`...")
    try:
        logging.info("Preparing to send morning greeting to user: %s", user_id)
        tconfig = read_yaml(TELEGRAM_CONFIG_PATH)
        user_id = tconfig.get(user_id, {}).get("chat_id")
        logging.debug("Resolved user ID: %s", user_id)

        msg = get_morning_greeting()
        logging.debug("Retrieved morning greeting message: %s", msg)

        sticker = get_morning_sticker()
        logging.debug("Retrieved morning sticker: %s", sticker)

        media = get_morning_media()
        logging.debug("Retrieved morning media: %s", media)

        await client.send_message(user_id, msg)
        logging.debug("Sent morning greeting message to user: %s", user_id)

        await client.send_message(
            user_id,
            file=InputDocument(
                id=sticker["id"],
                access_hash=sticker["access_hash"],
                file_reference=sticker["file_reference"],
            ),
        )
        logging.debug("Sent morning sticker to user: %s", user_id)

        await client.send_file(user_id, MEDIA_PATH / media["path"])
        logging.debug("Sent morning media to user: %s", user_id)
        logging.info("Morning greeting sent to user")

        if set_as_used:
            set_morning_sticker_as_used(sticker["uid"])
            set_morning_media_as_used(media["uid"])
            logging.debug("Marked sticker and media as used.")

    except FileNotFoundError as e:
        logging.error("Configuration or media file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML configuration: %s", e)
        raise e

    except Exception as e:
        logging.error("Error sending messages through Telegram client: %s", e)
        raise e

    logging.debug("Method `send_morning_greeting` finished.")


def start_sending_morning_greeting(
    scheduler: AsyncIOScheduler,
    client: TelegramClient,
    user_id: str = "nathy",
    try_today: bool = False,
):
    """Schedules the sending of morning greeting messages via Telegram.

    This function retrieves the configured start and end times for morning greetings, calculates a
    random time within that range, and schedules the greeting to be sent using the provided
    scheduler. It can also attempt to send the greeting for today if specified.

    Args:
        scheduler (AsyncIOScheduler): The scheduler instance used to manage scheduled jobs.
        client (TelegramClient): The Telegram client used to send messages.
        user_id (str, optional): The identifier for the user to whom the greeting is sent. Defaults
            to "nathy".
        try_today (bool, optional): If True, sends the greeting today if the calculated time has not
            passed. Defaults to False.
    """
    logging.debug("Running method `start_sending_morning_greeting`...")
    try:
        logging.info("Starting the scheduling of morning greetings for user: %s", user_id)
        tconfig = read_yaml(TELEGRAM_CONFIG_PATH)
        morning_greeting_time = tconfig.get(user_id, {}).get("morning_greeting", {})
        start_time = text_to_timedelta(morning_greeting_time.get("start_time"))
        end_time = text_to_timedelta(morning_greeting_time.get("end_time"))
        logging.info("Morning greeting time range: %s - %s", start_time, end_time)

        tm = random_time(start=start_time, end=end_time)
        logging.debug("Random time selected for morning greeting: %s", tm)

        dt = get_next_time(tm, timedelta(days=1), try_today)
        logging.info("Next greeting scheduled for: %s", dt)

        async def wrap(scheduler: AsyncIOScheduler, client: TelegramClient):
            """Wraps the process of sending a morning greeting and rescheduling it.

            This asynchronous function sends a morning greeting message using the provided Telegram
            client and then schedules the next morning greeting using the specified scheduler. It
            ensures that the greeting process is repeated at the appropriate time.

            Args:
                scheduler (AsyncIOScheduler): The scheduler instance used to manage the scheduling
                    of jobs.
                client (TelegramClient): The Telegram client used to send the greeting message.
            """
            logging.info("Sending morning greeting...")
            await send_morning_greeting(client)
            logging.info("Morning greeting sent. Rescheduling next greeting.")
            start_sending_morning_greeting(scheduler, client)

        global next_greeting_time
        next_greeting_time = dt
        logging.debug("Next greeting time set globally: %s", next_greeting_time)

        scheduler.add_job(wrap, "date", run_date=dt, args=[scheduler, client])
        logging.debug("Job added to scheduler for morning greeting at: %s", dt)

    except FileNotFoundError as e:
        logging.error("Configuration file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML configuration: %s", e)
        raise e

    except Exception as e:
        logging.error("Error scheduling morning greeting: %s", e)
        raise e

    logging.debug("Method `start_sending_morning_greeting` finished.")


async def send_afternoon_media(
    client: TelegramClient, user_id: str = "nathy", set_as_used: bool = True
):
    """Sends an afternoon media item to a specified user.

    This asynchronous function retrieves an afternoon media item and sends it to the specified user
    via a Telegram client. It can also mark the media item as used if specified.

    Args:
        client (TelegramClient): The Telegram client used to send the media.
        user_id (str, optional): The identifier for the user to whom the media is sent. Defaults to
            "nathy".
        set_as_used (bool, optional): Indicates whether to mark the media item as used after
            sending. Defaults to True.

    Raises:
        FileNotFoundError: If the configuration or media files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML configuration.
        Exception: If there is an error sending the media through the Telegram client.
    """
    logging.debug("Running method `send_afternoon_media`...")
    try:
        logging.info("Preparing to send afternoon media to user: %s", user_id)
        tconfig = read_yaml(TELEGRAM_CONFIG_PATH)
        user_id = tconfig.get(user_id, {}).get("chat_id")
        logging.debug("Resolved user ID: %s", user_id)

        media = get_afternoon_media()
        logging.debug("Retrieved afternoon media item: %s", media)

        await client.send_file(user_id, MEDIA_PATH / media["path"])
        logging.info("Afternoon media sent to user")

        if set_as_used:
            set_afternoon_media_as_used(media["uid"])
            logging.debug("Marked afternoon media as used for UID: %s", media["uid"])

    except FileNotFoundError as e:
        logging.error("Configuration or media file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML configuration: %s", e)
        raise e

    except Exception as e:
        logging.error("Error sending media through Telegram client: %s", e)
        raise e

    logging.debug("Method `send_afternoon_media` finished.")


def start_sending_afternoon_media(
    scheduler: AsyncIOScheduler,
    client: TelegramClient,
    user_id: str = "nathy",
    try_today: bool = False,
):
    """Schedules the sending of afternoon media messages via Telegram.

    This function retrieves the configured start and end times for afternoon media, calculates a
    random time within that range, and schedules the media to be sent using the provided scheduler.
    It can also attempt to send the media for today if specified.

    Args:
        scheduler (AsyncIOScheduler): The scheduler instance used to manage scheduled jobs.
        client (TelegramClient): The Telegram client used to send messages.
        user_id (str, optional): The identifier for the user to whom the greeting is sent. Defaults
            to "nathy".
        try_today (bool, optional): If True, sends the media today if the calculated time has not
            passed. Defaults to False.

    Raises:
        FileNotFoundError: If the configuration files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML configuration.
    """
    logging.debug("Running method `start_sending_afternoon_media`...")
    try:
        logging.info("Starting the scheduling of afternoon media for user: %s", user_id)
        tconfig = read_yaml(TELEGRAM_CONFIG_PATH)
        afternoon_media_time = tconfig.get(user_id, {}).get("afternoon_media", {})
        start_time = text_to_timedelta(afternoon_media_time.get("start_time"))
        end_time = text_to_timedelta(afternoon_media_time.get("end_time"))
        logging.debug("Afternoon media time range: %s - %s", start_time, end_time)

        tm = random_time(start=start_time, end=end_time)
        logging.debug("Random time selected for afternoon media: %s", tm)

        dt = get_next_time(tm, timedelta(days=1), try_today)
        logging.info("Next afternoon media scheduled for: %s", dt)

        async def wrap(scheduler: AsyncIOScheduler, client: TelegramClient):
            """Wraps the process of sending afternoon media and rescheduling it.

            This asynchronous function sends an afternoon media item using the provided Telegram client
            and then schedules the next afternoon media sending using the specified scheduler. It
            ensures that the media sending process is repeated at the appropriate time.

            Args:
                scheduler (AsyncIOScheduler): The scheduler instance used to manage the scheduling of
                    jobs.
                client (TelegramClient): The Telegram client used to send the media item.
            """
            logging.info("Sending afternoon media...")
            await send_afternoon_media(client)
            logging.info("Afternoon media sent. Rescheduling next media sending.")
            start_sending_afternoon_media(scheduler, client)

        global next_afternoon_media_time
        next_afternoon_media_time = dt
        logging.debug("Next afternoon media time set globally: %s", next_afternoon_media_time)

        scheduler.add_job(wrap, "date", run_date=dt, args=[scheduler, client])
        logging.debug("Job added to scheduler for afternoon media at: %s", dt)

    except FileNotFoundError as e:
        logging.error("Configuration file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML configuration: %s", e)
        raise e

    except Exception as e:
        logging.error("Error scheduling afternoon media: %s", e)
        raise e

    logging.debug("Method `start_sending_afternoon_media` finished.")


async def send_stats(client: TelegramClient, user_id: str):
    """Sends a message containing the remaining media items to a specified user.

    This asynchronous function retrieves the current state of media items and the register,
    calculates the remaining items for each media type, and sends a summary message to the
    specified user via the Telegram client.

    Args:
        client (TelegramClient): The Telegram client used to send the message.
        user_id (str): The identifier for the user to whom the message is sent.

    Raises:
        FileNotFoundError: If the specified YAML files cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML files.
        Exception: If there is an error sending the message through the Telegram client.
    """
    logging.debug("Running method `send_stats`...")
    try:
        logging.info("Preparing to send stats to user: %s", user_id)
        register = read_yaml(REGISTER_YAML_PATH)
        logging.debug("Loaded register data: %s", register)

        media_data = read_yaml(MEDIA_YAML_PATH)
        logging.debug("Loaded media data: %s", media_data)

        msg = "Remaining:"
        for data in (media_data,):
            for field in data:
                remaining_count = len(data[field]) - len(register[field])
                msg += f"\n  - {field}: {remaining_count}"
                logging.debug("Calculated remaining %s: %d", field, remaining_count)

        await client.send_message(user_id, msg)
        logging.info("Sent stats message to user %s: %s", user_id, msg.replace("\n", " | "))

    except FileNotFoundError as e:
        logging.error("YAML file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", e)
        raise e

    except Exception as e:
        logging.error("Error sending stats message through Telegram client: %s", e)
        raise e

    logging.debug("Method `send_stats` finished.")


def start_sending_pills_reminder(
    scheduler: AsyncIOScheduler, client: TelegramClient, user_id: str = "nathy"
):
    """Starts a scheduled reminder for taking pills via Telegram.

    This function configures a job in the provided scheduler to send a reminder message to a
    specified user at a designated time. The reminder message is sent repeatedly, adjusting the
    frequency based on the number of messages sent.

    Args:
        scheduler (AsyncIOScheduler): The scheduler to manage the reminder job.
        client (TelegramClient): The Telegram client used to send messages.
        user_id (str, optional): The ID of the user to send reminders to. Defaults to "nathy".

    Raises:
        FileNotFoundError: If the configuration file cannot be found.
        yaml.YAMLError: If there is an error parsing the YAML configuration.
        Exception: If there is an error scheduling the job or sending the message.
    """
    logging.debug("Running method `start_sending_pills_reminder`...")
    try:
        logging.info("Starting scheduled pill reminders for user: %s", user_id)
        tconfig = read_yaml(TELEGRAM_CONFIG_PATH)
        user = tconfig.get(user_id, {})
        user_id = user.get("chat_id")
        reminder_time = user.get("pills_reminder").get("time").split(":")
        logging.debug("Resolved chat ID: %s", user_id)
        logging.info("Pill reminder time set to: %s", reminder_time)

        async def wrap(client: TelegramClient):
            """Sends periodic pill reminder messages to a user via Telegram.

            This asynchronous function sends a reminder message to the specified user at regular
            intervals. The frequency of the messages adjusts dynamically based on the number of
            messages sent, ensuring that reminders are sent consistently without overwhelming the
            user.

            Args:
                client (TelegramClient): The Telegram client used to send messages.
            """
            global keep_sending_pill_reminder
            keep_sending_pill_reminder = True
            waiting_time, max_messages, cur_messages = 60, 5, 0
            logging.info(
                "Starting pill reminder loop for user %s with waiting time %d seconds and %d max "
                "messages",
                user_id,
                waiting_time,
                max_messages,
            )

            while keep_sending_pill_reminder:
                if cur_messages == max_messages:
                    waiting_time //= 2
                    max_messages *= 2
                    cur_messages = 0
                    logging.info(
                        "Adjusting waiting time to: %d seconds and max messages to: %d",
                        waiting_time,
                        max_messages,
                    )

                cur_messages += 1
                await client.send_message(
                    user_id, "💊 Amorcito, recuerda tomarte la píldora a las 10. Te amo ❤️"
                )
                logging.info("Sent pill reminder message to user: %s", user_id)
                await asyncio.sleep(waiting_time)

        scheduler.add_job(
            wrap,
            "cron",
            hour=reminder_time[0],
            minute=reminder_time[1],
            second=reminder_time[2],
            args=[client],
        )
        logging.info("Pill reminder job scheduled for user: %s at %s", user_id, reminder_time)

    except FileNotFoundError as e:
        logging.error("Configuration file not found: %s", e)
        raise e

    except yaml.YAMLError as e:
        logging.error("Error parsing YAML configuration: %s", e)
        raise e

    except Exception as e:
        logging.error("Error scheduling the pill reminder job: %s", e)
        raise e

    logging.debug("Method `start_sending_pills_reminder` finished.")


def handle_stop_sending_pill_reminder_for_today(client: TelegramClient):
    """Sets up an event handler to stop sending pill reminders for the day.

    This function configures an event handler that listens for incoming messages from a specific
    user and stops the pill reminder process when triggered. It retrieves the user's chat ID from
    the configuration and uses it to identify the relevant messages.

    Args:
        client (TelegramClient): The Telegram client used to add the event handler.
    """
    logging.debug("Running method `handle_stop_sending_pill_reminder_for_today`...")
    logging.info("Setting up event handler to stop sending pill reminders for today.")
    tconfig = read_yaml(TELEGRAM_CONFIG_PATH)
    nathy_id = tconfig.get("nathy", {}).get("chat_id")
    logging.debug("Resolved chat ID for user 'nathy': %s", nathy_id)

    async def handler(event: Message | events.NewMessage):
        """Handles the event to stop sending pill reminders.

        This asynchronous function is triggered by an incoming message event and sets a global flag
        to stop the pill reminder process. It ensures that no further reminders are sent once this
        event is processed.

        Args:
            event (Message | events.NewMessage): The event triggered by a new message.
        """
        logging.info("Received message to stop sending pill reminders.")
        global keep_sending_pill_reminder
        keep_sending_pill_reminder = False
        logging.info("Pill reminder sending has been stopped.")

    client.add_event_handler(handler, events.NewMessage(nathy_id, incoming=True))
    logging.debug("Event handler added for user 'nathy' to stop pill reminders.")
    logging.debug("Method `handle_stop_sending_pill_reminder_for_today` finished.")
