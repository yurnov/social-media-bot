# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

import os
import logging
from dotenv import load_dotenv

# Enable initial logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Check if the LOG_LEVEL is correct
if LOG_LEVEL.lower() not in ["debug", "info", "warning", "error", "critical"]:
    logger.warning("LOG_LEVEL is not correct. Defaulting to INFO")
    LOG_LEVEL = "INFO"
else:
    logger.info(f"Setting log level to {LOG_LEVEL.upper()}")

# Set the user-defined log level
logger.setLevel(LOG_LEVEL.upper())
