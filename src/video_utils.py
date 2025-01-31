# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

import os
import shutil
import subprocess
import tempfile
import yt_dlp  # Ensure yt_dlp is installed and available
from dotenv import load_dotenv
from logger import debug, error

load_dotenv()  # Load environment variables from .env file


def get_video_metadata(url):
    """
    Extract metadata from a video URL without downloading the content.

    Args:
        url (str): The URL of the video to analyze

    Returns:
        dict: Video metadata including duration, format, etc., or None if extraction fails

    Raises:
        yt_dlp.utils.ExtractorError: When video information cannot be extracted
    """
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
    }
    debug("Getting video metadata for: %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)  # fetch metadata only
            debug("Video metadata extracted")
            return info_dict
        except (yt_dlp.utils.ExtractorError, yt_dlp.utils.DownloadError) as e:
            debug("Extracting metadata failed: %s", e)
            return None
        except (ValueError, AttributeError) as e:  # Catch specific validation errors
            debug("Invalid video URL or metadata format for %s: %s", url, e)
            return None


def is_video_duration_over_limits(video_path: str, max_duration: int = 720) -> bool:
    """
    Checks if the video file is of a suitable size for compression.

    Args:
        video_path (str): The path to the video file to check.
        max_size_mb (int): The maximum file size in megabytes (default is 50MB).

    Returns:
        bool: True if the video file size is greater than the maximum size, False otherwise.
    """
    duration = get_video_duration(video_path)
    if duration:
        return duration > max_duration
    return False


def is_video_too_long_to_download(url, max_duration_minutes=12):
    """
    Checks if the video duration exceeds the specified maximum duration.

    Args:
        url (str): The URL of the video to check.
        max_duration_minutes (int): The maximum video duration in minutes (default is 12 minutes).

    Returns:
        bool: True if the video duration exceeds the maximum duration, False otherwise.
    """
    debug("Checking if video is too long to download: %s", url)
    metadata = get_video_metadata(url)
    if metadata and 'duration' in metadata:
        debug("Video duration: %s seconds. Max duration is %s seconds", metadata['duration'], max_duration_minutes * 60)
        return metadata['duration'] > (max_duration_minutes * 60)

    debug("No video duration found in metadata for %s", url)
    return False


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
        raise ValueError("Get video duration failed.")

    # bitrate caclulation kb/s (bit/sec -> kb/sec)
    target_bitrate_kbps = (target_size_bytes * 8) / duration / 1000
    debug("Starting compression for video: %s", input_path)

    command = [
        "nice",
        "-n",
        "19",
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
    except subprocess.CalledProcessError as e:
        error("Error while compressing: %s", e)
    debug("Compression completed for video: %s", input_path)


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
        error("Error getting video duration: %s", e)
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
        "--cookies",
        "/bot/cookies/instagram_cookies.txt",  # Use the path to your cookies file
        "-S",
        "vcodec:h264,fps,res,acodec:m4a",
        url,
        "-o",
        os.path.join(temp_dir, "%(id)s.%(ext)s"),
    ]

    debug("Downloading video from URL: %s", url)
    result_path = None  # Initialize the result variable

    try:
        subprocess.run(command, check=True, timeout=120)
        for filename in os.listdir(temp_dir):
            if filename.endswith(".mp4"):
                result_path = os.path.join(temp_dir, filename)
                break  # Exit the loop once the file is found
    except subprocess.CalledProcessError as e:
        error("Error downloading video: %s", e)
    except subprocess.TimeoutExpired as e:
        error("Download process timed out: %s", e)
    except (OSError, IOError) as e:
        error("File system error occurred: %s", e)
    except yt_dlp.utils.DownloadError as e:
        error("Download error occurred: %s", e)
    except yt_dlp.utils.ExtractorError as e:
        error("Extractor error occurred: %s", e)

    return result_path  # Return the result variable at the end


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
    debug("Video to delete %s", video_path)
    try:
        shutil.rmtree(os.path.dirname(video_path))
        debug("Video deleted %s", video_path)
    except (OSError, IOError) as cleanup_error:
        error("Error deleting file: %s", cleanup_error)
