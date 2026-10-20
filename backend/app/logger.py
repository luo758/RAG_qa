from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import BACKEND_DIR, settings


def setup_logging() -> None:
    log_dir = BACKEND_DIR / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(settings.log_level.upper())
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        log_dir / "backend.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(console)
    root.addHandler(file_handler)
