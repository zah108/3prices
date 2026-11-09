"""Entry point of the "Three Prices" system.

Run: python main.py  (from the project folder).
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

    # === Refresh quotes from MOEX (enabled by the DOWNLOAD_MOEX flag in config.py) ===
    if config.DOWNLOAD_MOEX:
        # Imported inside the condition: without the requests package installed,
        # the project keeps working with DOWNLOAD_MOEX = False — the data is
        # then taken from txt/ as is.
        import moex_loader
        moex_loader.download_moex_data(config.TXT_FOLDER, config.ASSETS_CONFIG, config.MOEX_DOWNLOAD_FROM)

    # === Read local data ===
    data_dict = data_loader.load_data(config.TXT_FOLDER, config.ASSETS_CONFIG, params.start_date)

    # === Compute the price level and color ===
    price_level_map, price_color_map = analysis.build_price_maps(data_dict)

    if not data_dict:
        # Fix: with empty data the script used to crash with a NameError on final_line
        logging.error("Нет данных для сохранения в PDF. Проверьте структуру файлов в папке txt")
        return 1

    # Fix: without the reports/ folder PdfPages used to crash with FileNotFoundError
    os.makedirs(config.REPORTS_FOLDER, exist_ok=True)
    pdf_path = os.path.join(config.REPORTS_FOLDER, params.pdf_filename)
    report.generate_pdf(pdf_path, data_dict, config.ASSETS_CONFIG, price_level_map, price_color_map, params)

    logging.info(f"Проанализировано: {len(data_dict)} тикеров")
    final_line = (f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"✅ Готово: {params.pdf_filename} — сохранён в папке {config.REPORTS_FOLDER}")
    print(final_line)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(final_line + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
