# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

import os
import shutil
import subprocess
import tempfile
from logger import debug, error
from dotenv import load_dotenv

load_dotenv()


def compress_video(input_path):
    """
    Compress video for 50MB with use of FFmpeg.

    Parameters:
        input_path (str): Path to original video.
    """

    temp_output = tempfile.mktemp(suffix=".mp4")
    # Caclulation of file size. 40 means MB
    target_size_bytes = 40 * 1024 * 1024
    duration = get_video_duration(input_path)
    if not duration:
        raise ValueError("Get video duration failed")

    # bitrate caclulation kb/s (bit/sec -> kb/sec)
    target_bitrate_kbps = (target_size_bytes * 8) / duration / 1000

    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-b:v",
        f"{target_bitrate_kbps}k",
        "-vf",
        "scale=-2:720",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-y",
        temp_output,
    ]

    try:
        subprocess.run(command, check=True)
        if os.path.exists(temp_output):
            os.replace(temp_output, input_path)
            debug(f"Compressed done. File saved: {input_path}")
    except subprocess.CalledProcessError as e:
        error(f"Error while compressing: {e}")


def get_video_duration(video_path):
    """
    Gets video duration in seconds.
    """
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        error(f"Error getting video duration: {e}")
        return None


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
        "-S",
        "vcodec:h264,fps,res,acodec:m4a",
        url,
        "-o",
        os.path.join(temp_dir, "%(id)s.%(ext)s"),
    ]

    try:
        subprocess.run(command, check=True, timeout=120)
        for filename in os.listdir(temp_dir):
            if filename.endswith(".mp4"):
                return os.path.join(temp_dir, filename)
        return None
    except subprocess.CalledProcessError as e:
        error(f"Error downloading video: {e}")
        return None
    except subprocess.TimeoutExpired as e:
        error(f"Download process timed out: {e}")
        return None
    except (OSError, IOError) as e:
        error(f"File system error occurred: {e}")
        return None


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
    debug(f"Video to delete {video_path}")
    try:
        shutil.rmtree(os.path.dirname(video_path))
        debug(f"Video deleted {video_path}")
    except (OSError, IOError) as cleanup_error:
        error(f"Error deleting file: {cleanup_error}")
