from config.metadata import PIPELINE_NAME, PIPELINE_VERSION
from config.settings import settings

from datetime import datetime
import functools
import logging
import pytz
import time

# ANSI colors (dev only)
LOG_COLORS = {
    "DEBUG": "\033[94m",     # Blue
    "INFO": "\033[92m",      # Green
    "WARNING": "\033[93m",   # Yellow
    "ERROR": "\033[91m",     # Red
    "CRITICAL": "\033[95m",  # Magenta
}
_CYAN = "\033[96m"
_GRAY = "\033[90m"
_RESET = "\033[0m"

TZ_PST = pytz.timezone("Canada/Pacific")


class MicrosecondColoredFormatter(logging.Formatter):
    """
    Custom formatter:
    - Adds microsecond timestamps
    - Converts to Pacific Time
    - Adds color to log levels in dev
    """

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, TZ_PST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%H:%M:%S.%f")

    def format(self, record):
        # Colorize level name (dev only)
        if settings.ENV not in ("prod", "production"):
            color = LOG_COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname}{_RESET}"

        return super().format(record)


def setup_logger(logger_name, log_level=None, env=settings.ENV):
    """
    Set up a logger with Pacific Time timestamps and custom formatting.
    """

    logger = logging.getLogger(logger_name)

    # Reset handlers & propagation
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.StreamHandler()

    # DEV → colored + timestamps + microseconds
    if env not in ("prod", "production"):
        formatter = MicrosecondColoredFormatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            #datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # PROD → clean, no color
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Log level
    if log_level is None:
        log_level = logging.DEBUG if env not in ("prod", "production") else logging.INFO
    logger.setLevel(log_level)

    return logger


def log_function_call(logger):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            start_msg = (
                f"{_GRAY}>>> Starting {func.__name__}{_RESET}"
                if settings.ENV not in ("prod", "production")
                else f">>> Starting {func.__name__}"
            )
            logger.info(start_msg)

            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                end_msg = (
                    f"{_GRAY}<<< Finished {func.__name__} "
                    f"| Duration: {elapsed:.2f}s{_RESET}"
                    if settings.ENV not in ("prod", "production")
                    else f"<<< Finished {func.__name__} | Duration: {elapsed:.2f}s"
                )
                logger.info(end_msg)

        return wrapper
    return decorator


def log_environment_startup(logger):
    if settings.ENV not in ("prod", "production"):
        logger.info(f"{_CYAN}{PIPELINE_NAME} | Version: {PIPELINE_VERSION} | Environment: {settings.ENV}{_RESET}")
    else:
        logger.info(f"{PIPELINE_NAME} | Version: {PIPELINE_VERSION} | Environment: {settings.ENV}")


logger = setup_logger(__name__)
log_environment_startup(logger)