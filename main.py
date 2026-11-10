"""Точка входа системы «3price».

Запуск: python main.py  (из папки проекта).
"""

import logging
import os
import sys
from datetime import datetime

import analysis
import config
import data_loader
import log_setup
import report


def main() -> int:
    params = config.build_run_params()
    log_path = log_setup.setup_logging(config.LOGS_FOLDER, params.log_filename)
    log_setup.write_banner(log_path)

    # === Список активов текущей страны ===
    if config.COUNTRY == 'RF':
        assets_config = config.ASSETS_CONFIG_RF
    elif config.COUNTRY == 'USA':
        assets_config = config.ASSETS_CONFIG_USA
    else:
        logging.error(f"Неизвестное значение COUNTRY: {config.COUNTRY!r} — допустимо 'RF' или 'USA'")
        return 1

    # === Обновление котировок с рынка текущей страны ===
    if config.COUNTRY == 'RF' and config.DOWNLOAD_MOEX:
        # Импорт внутри условия: без пакета requests проект работает и без сети.
        import moex_loader
        moex_loader.download_moex_data(config.TXT_FOLDER, assets_config,
                                       config.DOWNLOAD_FROM, config.COUNTRY)
    elif config.COUNTRY == 'USA' and config.DOWNLOAD_USA:
        # Аналогично: без пакета yfinance проект работает и без сети.
        import usa_loader
        usa_loader.download_usa_data(config.TXT_FOLDER, assets_config,
                                     config.DOWNLOAD_FROM, config.COUNTRY)

    # === Чтение локальных данных ===
    data_dict = data_loader.load_data(config.TXT_FOLDER, assets_config,
                                      params.start_date, config.COUNTRY)

    # === Расчёт ценового уровня и цвета ===
    price_level_map, price_color_map = analysis.build_price_maps(data_dict)

    if not data_dict:
        # Раньше на пустых данных скрипт падал ниже с NameError
        logging.error("Нет данных для сохранения в PDF. Проверьте структуру файлов в папке txt")
        return 1

    # Без папки reports/ PdfPages падал с FileNotFoundError
    os.makedirs(config.REPORTS_FOLDER, exist_ok=True)
    pdf_path = os.path.join(config.REPORTS_FOLDER, params.pdf_filename)
    report.generate_pdf(pdf_path, data_dict, assets_config, price_level_map, price_color_map, params)

    logging.info(f"Проанализировано: {len(data_dict)} тикеров")
    final_line = (f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"✅ Готово: {params.pdf_filename} — сохранён в папке {config.REPORTS_FOLDER}")
    print(final_line)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(final_line + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
