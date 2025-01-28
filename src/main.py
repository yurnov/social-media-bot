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
from logger import error, info
from video_utils import compress_video, download_video, cleanup_file
from permissions import is_user_or_chat_not_allowed, supported_sites

load_dotenv()

language = os.getenv("LANGUAGE", "ua").lower()  # Default to Ukrainian if not set

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
        return [
            "Sorry, I'm having trouble loading my responses right now! 😅",
            "Вибачте, у мене проблеми із завантаженням відповідей! 😅",
        ]


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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):  # pylint: disable=unused-argument
    """
    Handles incoming messages from the Telegram bot.

    This function processes text messages sent to the bot and determines the appropriate response
    based on the message content. It supports specific keywords and URLs, such as Instagram Reels
    , or other supported sites, and attempts to download and send the corresponding video.

    Parameters:
        update (telegram.Update): Represents the incoming update from the Telegram bot.
        context (ContextTypes.DEFAULT_TYPE): The context object for the handler.

    Behavior:
        - If the message contains "ботяра" (case insensitive), responds with a random response
          from a predefined list.
        - If the message contains an Instagram Stories URL, informs the user that login is required.
        - If the message contains a supported URL (Instagram Reels, Facebook Reels, Youtube Shorts, TikTok, Reddit, X/Twitter):
            - Downloads and optionally compresses the video
            - Sends the video back to the user via Telegram
            - Preserves spoiler tags if present in original message
            - Cleans up temporary files after sending
        - Handles various error cases with appropriate user feedback

    Returns:
        None
    """
    if not update.message or not update.message.text:
        return

    message_text = update.message.text.strip()

    # Handle bot mention response
    if "ботяра" in message_text.lower() or "bot_health" in message_text.lower():
        await update.message.reply_text(random.choice(responses))
        return

    # Check if user is not allowed
    if is_user_or_chat_not_allowed(update.effective_user.username, update.effective_chat.id):
        await update.message.reply_text(
            f"You are not allowed to use this bot. "
            f"Your username is {update.effective_user.username} "
            f"and chat id is {update.effective_chat.id}"
        )
        return

    # Handle Instagram stories
    if "instagram.com/stories/" in message_text:
        if language == "ua":
            await update.message.reply_text("Сторіз не можу скачати.")
        else:
            await update.message.reply_text("Instagram stories not supported.")
        return

    message_text = message_text.replace("** ", "**")

    # Check if URL is from a supported site
    if not any(site in message_text for site in supported_sites):
        if language == "ua":
            await update.message.reply_text("Цей сайт не підтримується. Спробуйте додати ** перед URL")
        else:
            await update.message.reply_text("This site is not supported. Try adding ** before the URL")
        return

    try:
        # Remove '**' prefix and any spaces if present
        url = message_text.replace("**", "") if message_text.startswith("**") else message_text

        # Download the video
        video_path = download_video(url)
        # Check if video was downloaded
        if not video_path or not os.path.exists(video_path):
            return

        # Compress video if it's larger than 50MB
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        if file_size_mb > 50:
            compress_video(video_path)

        # Check for spoiler flag
        has_spoiler = spoiler_in_message(update.message.entities)

        # Send the video to the chat
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
        except (NetworkError, TelegramError):
            await update.message.reply_text(
                (
                    f"О kurwa! Compressed file size: "
                    f"{os.path.getsize(video_path) / (1024 * 1024):.2f}MB. "
                    f"Telegram API Max is 50MB"
                )
            )

    finally:
        # Clean up temporary files
        if video_path and os.path.exists(video_path):
            cleanup_file(video_path)


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
    info("Bot started. Ctrl+C to stop")
    application.run_polling()


if __name__ == "__main__":
    main()
