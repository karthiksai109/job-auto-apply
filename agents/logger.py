"""
Centralized logging for all agents.
Each agent gets its own named logger that writes to both console and file.
"""
import logging
import os
from datetime import datetime
from agents.config import LOG_DIR


def get_logger(agent_name: str) -> logging.Logger:
    """Create a logger for a specific agent."""
    logger = logging.getLogger(f"JobBot.{agent_name}")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler (per-agent log file)
    log_file = os.path.join(LOG_DIR, f"{agent_name.lower()}.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter(
        f"%(asctime)s | [{agent_name:^12}] | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
