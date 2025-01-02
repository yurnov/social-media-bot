"""Download videos from tiktok, x(twitter), reddit, and insta reels"""
import os
import random
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.error import TimedOut
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import MessageEntityType
from logger import print_logs
from video_utils import compress_video, download_video, cleanup_file

load_dotenv()
supported_sites = ["instagram.com/", "tiktok.com/", "reddit.com/", "//x.com/", "**https:"]

def load_responses():
    """Function loading bot responses."""
    with open("responses.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    return data["responses"]


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


responses = load_responses()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE): # pylint: disable=unused-argument
    """
    Handles incoming messages from the Telegram bot.

    This function processes text messages sent to the bot and determines the appropriate response
    based on the message content. It supports specific keywords and URLs, such as Instagram Reels
    and TikTok links, and attempts to download and send the corresponding video.

    Parameters:
        update (telegram.Update): Represents the incoming update from the Telegram bot.

    Behavior:
        - If the message contains "ботяра" (case insensitive), responds with a random response
          from a predefined list.
        - If the message contains an Instagram Stories URL, informs the user that login is required.
        - If the message contains an Instagram Reels or TikTok URL:
            - Sends a "please wait" message to the user.
            - Downloads the video using the `download_video` function.
            - Sends the downloaded video back to the user via Telegram.
            - Cleans up the temporary file after sending the video.
        - If the video download or sending fails, notifies the user with an error message.

    Exceptions:
        - Handles `telegram.error.TimedOut` errors if sending the video to Telegram times out.
        - Logs unexpected errors during the video sending or download process.

    Notes:
        - Assumes the `download_video` function is implemented and working correctly.
        - Uses a predefined list of responses for the "ботяра" keyword.
        - Deletes temporary files and directories after successfully handling a video.

    Returns:
        None
    """
    if not update.message or not update.message.text:
        return
    url = update.message.text

    if "ботяра" in url.lower():
        response = random.choice(responses)
        await update.message.reply_text(response)
        return
    
    if "instagram.com/stories/" in url:
        await update.message.reply_text("Сторіз не можу скачати. Треба логін")
        return
    
    if any(site in url for site in supported_sites):
        url = url[2:] if url.startswith("**") else url  # Remove '**' if present

        # Download the video
        video_path = download_video(url)

        if not video_path or not os.path.exists(video_path):
            return
        
        # Compress video if it's larger than 50MB
        if os.path.getsize(video_path) / (1024 * 1024) > 50:
            compress_video(video_path)

        # Check if the message has a spoiler
        visibility_flag = spoiler_in_message(update.message.entities)

        # Send the video to the chat
        try:
            with open(video_path, 'rb') as video_file:
                await update.message.chat.send_video(
                    video=video_file,
                    has_spoiler=visibility_flag,
                    disable_notification=True,
                    write_timeout=8000,
                    read_timeout=8000
                )
        except TimedOut as e:
            print_logs(f"Telegram timeout while sending video. {e}")
        except Exception:
            await update.message.reply_text(
                f"О kurwa! Compressed file size: {os.path.getsize(video_path) / (1024 * 1024):.2f}MB. Telegram API Max is 50MB"
            )

        # Clean up the video file after sending
        cleanup_file(video_path)
    else:
        return


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
    print("Bot started. Ctrl+C to stop")
    application.run_polling()


if __name__ == "__main__":
    main()
