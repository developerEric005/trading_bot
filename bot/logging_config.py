import logging
import os
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

FILE_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
CONSOLE_FMT = "%(levelname)-8s | %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(FILE_FMT, datefmt=DATE_FMT))

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(CONSOLE_FMT, datefmt=DATE_FMT))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
