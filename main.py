"""Download videos from tiktok and insta reels"""
import os
import subprocess
import tempfile
import random
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.error import TimedOut
from telegram.ext import Application, MessageHandler, filters, ContextTypes


load_dotenv()
show_errors_in_console = os.getenv("DEBUG")


def print_logs(text):
    """Prints a log message to the console if debugging is enabled."""
    if show_errors_in_console:
        print(text)


def load_responses():
    """Function loading bot responses."""
    with open("responses.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    return data["responses"]


responses = load_responses()


def cleanup_file(video_path):
    """
    Deletes a video file and its containing directory.

    This function attempts to remove the specified video file and 
    its parent directory. Logs are printed if debugging is enabled.

    Parameters:
        video_path (str): The path to the video file to delete.

    Logs:
        Logs messages about the deletion process or any errors encountered.
    """
    print_logs(f"Video to delete {video_path}")
    try:
        os.remove(video_path)
        os.rmdir(os.path.dirname(video_path))
        print_logs(f"Video deleted {video_path}")
    except Exception as cleanup_error:
        print_logs(f"Error deleting file: {cleanup_error}")


def download_video(url):
    """
    Downloads a video from the specified URL using yt-dlp and saves it as an MP4 file.

    This function uses the `yt-dlp` command-line tool to download a video. The video is stored
    in a temporary directory with a filename based on the video's title. The function
    returns the path to the downloaded video file if successful.

    Parameters:
        url (str): The URL of the video to download.

    Returns:
        str: The path to the downloaded MP4 video file if successful, or None if the download fails.

    Exceptions:
        Handles exceptions for subprocess errors, timeouts, or unexpected errors during the
        download process. Logs the errors if debugging is enabled.
    """
    temp_dir = tempfile.mkdtemp()
    command = [
        "yt-dlp",  # Assuming yt-dlp is installed and in the PATH
        "-S", "vcodec:h264,fps,res,acodec:m4a",
        url,
        "-o", os.path.join(temp_dir, "%(title)s.%(ext)s")
    ]

    try:
        subprocess.run(command, check=True, timeout=120)
        for filename in os.listdir(temp_dir):
            if filename.endswith(".mp4"):
                return os.path.join(temp_dir, filename)
        return None
    except subprocess.CalledProcessError as e:
        print_logs(f"Error downloading video: {e}")
        return None
    except subprocess.TimeoutExpired as e:
        print_logs(f"Download process timed out: {e}")
        return None
    except Exception as e:
        print_logs(f"An unexpected error occurred: {e}")
        return None


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

    elif "instagram.com/stories/" in url:
        await update.message.reply_text("Сторіз не можу скачати. Треба логін")

    elif "instagram.com/reel/" in url or "tiktok.com/" in url or "reddit.com" in url or "x.com" in url:
        # wait_message = await update.message.reply_text("Почекай пару сек...")

        video_path = download_video(url)

        if video_path and os.path.exists(video_path):
            with open(video_path, 'rb') as video_file:
                try:
                    await update.message.reply_video(video_file)
                    # await wait_message.delete()
                except TimedOut as e:
                    print_logs(f"Telegram timeout while sending video. {e}")
                except Exception as e:
                    await update.message.reply_text(f"О Курва! Якась помилка. Спробуй ще. {e}")
                    return None
            cleanup_file(video_path) # Delete video after sending to tg
        else:
            pass
            # await wait_message.delete()
            # await update.message.reply_text("О Курва! Якась помилка. Спробуй ще.")
    else:
        pass


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
