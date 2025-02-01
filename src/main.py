"""Download videos from tiktok, x(twitter), reddit, youtube shorts, instagram reels and many more"""

import os
import random
import json
from functools import lru_cache
from dotenv import load_dotenv
from telegram import Update
from telegram.error import TimedOut, NetworkError, TelegramError
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import MessageEntityType
from logger import error, info, debug
from permissions import inform_user_not_allowed, is_user_or_chat_not_allowed, supported_sites
from video_utils import (
    compress_video,
    download_video,
    cleanup_file,
    is_video_duration_over_limits,
    is_video_too_long_to_download,
)

load_dotenv()

# Default to Ukrainian if not set
language = os.getenv("LANGUAGE", "ua").lower()
admins_chat_ids = os.getenv("ADMINS_CHAT_IDS")
send_error_to_admin = os.getenv("SEND_ERROR_TO_ADMIN", "False").lower() == "true"


# Cache responses from JSON file
@lru_cache(maxsize=1)
def load_responses():
    """Function loading bot responses based on language setting."""

    filename = "responses_ua.json" if language == "ua" else "responses_en.json"
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data["responses"]
    except FileNotFoundError:
        # Return a minimal set of responses if no response files found
        not_found_responses = {
            "en": "Sorry, I'm having trouble loading my responses right now! 😅",
            "ua": "Вибачте, у мене проблеми із завантаженням відповідей! 😅",
        }
        return not_found_responses[language]


responses = load_responses()


def spoiler_in_message(entities):
    """
    Checks if any of the provided message entities contain a spoiler.

    This function iterates through the list of message entities and checks if
    any of them have the type `MessageEntityType.SPOILER`.

    Args:
        entities (list): A list of `MessageEntity` objects from a Telegram message.
                         These entities describe parts of the message (e.g., bold text,
                         spoilers, mentions, etc.).

    Returns:
        bool: True if a spoiler entity is found, False otherwise.

    Example:
        entities = [
            MessageEntity(length=65, offset=0, type=MessageEntityType.SPOILER),
            MessageEntity(length=10, offset=70, type=MessageEntityType.BOLD)
        ]
        spoiler_in_message(entities)  # Returns: True
    """
    if entities:
        for entity in entities:
            if entity.type == MessageEntityType.SPOILER:
                return True
    return False


def is_bot_mentioned(message_text: str) -> bool:
    """
    Checks if the bot is mentioned in the message text.

    Args:
        message_text (str): The text of the message to check.

    Returns:
        bool: True if the bot is mentioned, False otherwise.
    """
    bot_trigger_words = ["ботяра", "bot_health"]
    return any(word in message_text.lower().split() for word in bot_trigger_words)


def clean_url(message_text: str) -> str:
    """
    Cleans the URL from the message text by removing unwanted characters.

    Args:
        message_text (str): The text of the message containing the URL.

    Returns:
        str: The cleaned URL.
    """
    return message_text.replace("**", "") if message_text.startswith("**") else message_text


def is_large_file(file_path: str, max_size_mb: int = 50) -> bool:
    """
    Checks if the file size exceeds the specified maximum size.

    Args:
        file_path (str): The path to the file to check.
        max_size_mb (int): The maximum file size in megabytes (default is 50MB).

    Returns:
        bool: True if the file size exceeds the maximum size, False otherwise.
    """
    return os.path.exists(file_path) and (os.path.getsize(file_path) / (1024 * 1024)) > max_size_mb


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log the error and send a message to the admins.
    Works only if SEND_ERROR_TO_ADMIN=True in .env file. and ADMINS_CHAT_IDS is set.
    If SEND_ERROR_TO_ADMIN=False, the error will be logged but not sent to admins.
    Works only for Exceptions errors that are not handled by the bot code.
    """
    if update is None or update.effective_sender is None:
        error("Update or effective_sender is None. Cannot log error.")
        return  # Exit the function if update is not valid

    username = update.effective_sender.username
    debug("User username: %s", username)
    # Log the error
    debug("Update %s caused error %s", update, context.error)
    debug("send_error_to_admin: %s, admin_chat_id: %s", send_error_to_admin, admins_chat_ids)
    if send_error_to_admin and admins_chat_ids:
        admin_ids = admins_chat_ids.split(",")  # Split the string into a list of IDs
        for admin_chat_id in admin_ids:
            await context.bot.send_message(
                chat_id=admin_chat_id.strip(),  # Strip any whitespace
                text=f"`{context.error}` \n\nWho triggered the error: `@{username}`.\nUrl was {update.message.text}",
                disable_web_page_preview=True,
                parse_mode='Markdown',
            )
    else:
        debug("Admin chat IDs are not set; error message not sent to admins.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):  # pylint: disable=unused-argument
    """
    Handles incoming messages from the Telegram bot.

    This function processes text messages sent to the bot and determines the appropriate response
    based on the message content. It supports specific keywords and URLs, such as Instagram Reels,
    Facebook Reels, YouTube Shorts, TikTok, Reddit, and X/Twitter, and attempts to download and send
    the corresponding video to the user.

    Parameters:
        update (telegram.Update): Represents the incoming update from the Telegram bot.
        context (ContextTypes.DEFAULT_TYPE): The context object for the handler.

    Behavior:
        - If the message contains "ботяра" (case insensitive), responds with a random response
          from a predefined list of bot responses.
        - If the message contains an Instagram Stories URL, informs the user that downloading is not supported.
        - If the message contains a supported URL
          (Instagram Reels, Facebook Reels, YouTube Shorts,
          TikTok, Reddit, X/Twitter):
            - Downloads and optionally compresses the video.
            - Sends the video back to the user via Telegram.
            - Preserves any spoiler tags present in the original message.
            - Cleans up temporary files after sending the video.
        - Handles error cases with appropriate user feedback, ensuring a smooth user experience.

    Returns:
        None
    """
    video_path = None
    if not update.message or not update.message.text:
        return

    debug("Received a new message: %s", update.message.text)

    message_text = update.message.text.strip()

    # Handle bot mention response
    if is_bot_mentioned(message_text):
        await respond_with_bot_message(update)
        return

    # Ignore if message doesn't contain http
    if "http" not in message_text:
        return

    # Check if user is not allowed
    if is_user_or_chat_not_allowed(update.effective_user.username, update.effective_chat.id):
        await inform_user_not_allowed(update)
        return

    message_text = message_text.replace("** ", "**")

    # Check if URL is from a supported site. Ignore if it's from a group or channel
    if not any(site in message_text for site in supported_sites):
        if update.effective_chat.type == "private":
            not_supported_responses = {
                "ua": "Цей сайт не підтримується. Спробуйте додати ** перед https://",
                "en": "This site is not supported. Try adding ** before the https://",
            }
            await update.message.reply_text(not_supported_responses[language])
            return  # Stop further execution after sending the reply
        return

    debug("Cleaning URL from message text.")
    url = clean_url(message_text)
    debug("Cleaned URL: %s", url)

    if is_video_too_long_to_download(url):
        debug("Video is too long to process.")
        await update.message.reply_text("The video is too long to send (over 12 minutes).")
        return
    debug("Video is not too long or metadata is not available. Starting download.")

    try:
        # media_path can be string or list of strings
        media_path = download_video(url)
        video_path = [] # Initilize empty list of video paths
        pic_path = [] # Initilize empty list of picture paths

        for path in media_path:
            debug("Media downloaded to: %s", video_path)

            # Create a lists of video and picture paths
            if path.endswith(".mp4"):
                video_path.append(path)
            elif path.endswith(".jpg", ".jpeg", ".png"):
                pic_path.append(path)

        for video in video_path:
            # Compress video if it's larger than 50MB
            # do not process compression if video is too long
            if is_video_duration_over_limits(video):
                await update.message.reply_text("The video is too large to send (over 50MB).")
                continue  # Drop the video and continue to the next one

            if is_large_file(video):
                compress_video(video)

            # Check for spoiler flag
            has_spoiler = spoiler_in_message(update.message.entities)

            if is_large_file(video):
                await update.message.reply_text("The video is too large to send (over 50MB).")
                continue  # Stop further execution for this video

            # Send the video to the chat
            await send_video(update, video, has_spoiler)

    for pic in pic_path:
        # Send the picture to the chat
        with open(pic, 'rb') as pic_file:
            await update.message.chat.send_photo(
                photo=pic_file,
                disable_notification=True,
                write_timeout=8000,
                read_timeout=8000,
            )


    finally:
        if media_path:
            cleanup_file(media_path)


async def respond_with_bot_message(update: Update) -> None:
    """
    Responds to the user with a random bot response when the bot is mentioned.

    Args:
        update (telegram.Update): Represents the incoming update from the Telegram bot.

    Returns:
        None
    """
    response_message = random.choice(responses)  # Select a random response from the predefined list
    await update.message.reply_text(
        f"{response_message}\n"
        f"[Chat ID]: {update.effective_chat.id}\n"
        f"[Username]: {update.effective_user.username}"
    )


async def send_video(update: Update, video_path: str, has_spoiler: bool) -> None:
    """
    Sends the video to the chat.

    Args:
        update (telegram.Update): Represents the incoming update from the Telegram bot.
        video_path (str): The path to the video file to send.
        has_spoiler (bool): Indicates if the message contains a spoiler.

    Returns:
        None
    """
    try:
        with open(video_path, 'rb') as video_file:
            await update.message.chat.send_video(
                video=video_file,
                has_spoiler=has_spoiler,
                disable_notification=True,
                write_timeout=8000,
                read_timeout=8000,
            )
    except TimedOut as e:
        error("Telegram timeout while sending video. %s", e)
    except (NetworkError, TelegramError) as e:
        await update.message.reply_text(f"Error sending video: {str(e)}. Please try again later.")


def main():
    """
    Entry point for the Telegram bot application.

    This function initializes the bot, sets up message handling, and starts the bot's polling loop.

    Steps:
        1. Retrieves the bot token from the environment variable `BOT_TOKEN`.
        2. Builds a Telegram bot application using the `Application.builder()` method.
        3. Adds a message handler to process all text messages (excluding commands) using the
           `handle_message` function.
        4. Prints a message to indicate the bot has started.
        5. Starts the bot's polling loop, allowing it to listen for incoming updates until
           manually stopped (Ctrl+C).

    Dependencies:
        - Requires the `BOT_TOKEN` environment variable to be set with the bot's token.
        - Depends on `handle_message` for processing incoming messages.

    Notes:
        - Designed to be run as the `__main__` function in a Python script.
        - Uses the `telegram.ext.Application` and `MessageHandler` from the Telegram Bot API library.

    Returns:
        None
    """
    bot_token = os.getenv("BOT_TOKEN")
    application = Application.builder().token(bot_token).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # This handler will receive every error which happens in your bot
    application.add_error_handler(error_handler)
    info("Bot started. Ctrl+C to stop")
    application.run_polling()


if __name__ == "__main__":
    main()
