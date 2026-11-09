"""Logging setup and the startup banner of the "Three Prices" system.

The module is named log_setup, not logging: a logging.py file in the project
root would shadow the standard logging module and break the pandas/matplotlib
imports.
"""

import logging
import os
from datetime import datetime


def setup_logging(logs_folder: str, log_filename: str) -> str:
    """Set up simultaneous log output to a file and to the console.

    Creates the logs folder when needed. Returns the log file path — it is
    needed for lines that are written to the log without the logging prefix.
    """
    os.makedirs(logs_folder, exist_ok=True)
    log_path = os.path.join(logs_folder, log_filename)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(),
        ],
    )
    return log_path


def write_banner(log_path: str) -> None:
    """Write the startup banner to the console and to the log without the
    standard logging prefix."""
    banner_lines = [
        "",
        "=" * 48,
        f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] 🚀 Запуск системы "Три цены" 3price.',
        "=" * 48,
    ]
    with open(log_path, 'a', encoding='utf-8') as f:
        for line in banner_lines:
            print(line)
            f.write(line + '\n')
