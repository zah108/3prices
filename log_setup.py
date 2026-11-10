"""Настройка логирования и стартовый баннер системы «Три цены».
Модуль назван log_setup, а не logging: файл logging.py затенил бы
стандартный модуль logging и сломал импорты pandas/matplotlib."""

import logging
import os
from datetime import datetime


def setup_logging(logs_folder: str, log_filename: str) -> str:
    """Настройка одновременного вывода лога в файл и в консоль.

    Создаёт папку logs при необходимости, возвращает путь к лог-файлу.
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
    """Стартовый баннер в консоль и в лог без стандартного префикса logging."""
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
