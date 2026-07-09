"""Logging setup.

Provides a module-level logger ``log`` and :func:`configure_logging` to apply
the configured level + a uniform format. Worker code imports the same logger
so all output is consistent.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(level: str = "INFO", log_dir: Path | None = None) -> None:
    """Configure root logging exactly once with console (+ optional file) output."""
    global _configured
    if _configured:
        # Still allow the level to be nudged on a re-call.
        logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter = logging.Formatter(_FORMAT, _DATEFMT)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "fgobot.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# Convenience module-level logger.
log = logging.getLogger("fgobot")
