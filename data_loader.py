"""Чтение локальных котировок из txt-файлов папки txt."""

import glob
import logging
import os

import pandas as pd


def _extract_ticker(file_name: str, country: str) -> str | None:
    """Тикер из имени файла с префиксом страны: 'RF-SBER-d.txt' -> 'SBER'.
    Склеенный фьючерс Yahoo хранится как 'USA-ZW-F-d.txt' -> 'ZW=F'."""
    prefix = f'{country}-'
    if not file_name.startswith(prefix):
        return None
    stem = file_name[len(prefix):]
    if not stem.endswith('-d.txt'):
        return None
    ticker = stem[:-len('-d.txt')]
    # Непрерывный фьючерс Yahoo 'ZW=F' сохранён как 'ZW-F' — вернём исходный тикер
    if ticker.endswith('-F'):
        ticker = ticker[:-2] + '=F'
    return ticker


def _parse_price_file(file_path: str) -> pd.DataFrame:
    """Чтение CSV с произвольным разделителем и нормализация колонок даты/цены."""
    df = pd.read_csv(file_path, sep=None, engine='python')
    df.columns = [str(col).strip().lower().replace('<', '').replace('>', '') for col in df.columns]

    date_col = None
    for possible_date in ['begin', 'date', 'timestamp', 'time']:
        if possible_date in df.columns:
            date_col = possible_date
            break

    close_col = None
    for possible_close in ['close', 'last', 'price']:
        if possible_close in df.columns:
            close_col = possible_close
            break

    if not date_col or not close_col:
        raise ValueError('не найдены колонки даты или цены. Доступные: ' + str(list(df.columns)))

    df = df.rename(columns={date_col: 'begin', close_col: 'close'})
    df['begin'] = pd.to_datetime(df['begin'], errors='coerce')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df = df.dropna(subset=['begin', 'close']).sort_values('begin').reset_index(drop=True)
    df['close'] = df['close'].round(2)
    return df


def load_data(txt_folder: str, assets_config: dict, start_date: pd.Timestamp,
              country: str) -> dict[str, pd.DataFrame]:
    """Чтение подходящих файлов; возвращает {тикер: DataFrame} от start_date.
    Читаются только файлы с префиксом страны; тикеры вне assets_config молча
    пропускаются, битый файл даёт лишь запись в лог."""
    all_files = glob.glob(os.path.join(txt_folder, f'{country}-*-d.txt'))

    data_dict: dict[str, pd.DataFrame] = {}
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        ticker = _extract_ticker(file_name, country)

        if ticker is None or ticker not in assets_config:
            continue

        try:
            df = _parse_price_file(file_path)
        except ValueError as e:
            logging.error(f"В файле {file_name} {e}")
            continue
        except Exception as e:
            logging.error(f"Ошибка обработки {file_name}: {e}")
            continue

        df = df[df['begin'] >= start_date].reset_index(drop=True)

        if df.empty:
            logging.warning(f"Файл {file_name} не содержит данных после {start_date.strftime('%Y-%m-%d')}")
            continue

        data_dict[ticker] = df
        logging.info(f"Успешно прочитан файл: {file_name} ({len(df)} строк начиная с {start_date.strftime('%Y-%m-%d')})")

    # Файлы без префикса страны (новые и старые суффиксы) не читаются — предупреждаем
    for suffix in ('-d.txt', '-d-5y.txt', '-all-d.txt'):
        for legacy_path in glob.glob(os.path.join(txt_folder, f'*{suffix}')):
            legacy_name = os.path.basename(legacy_path)
            if legacy_name.startswith(f'{country}-'):
                continue
            base = legacy_name[:-len(suffix)]
            if _extract_ticker(f'{country}-{base}-d.txt', country) in assets_config:
                logging.warning(
                    f"Файл {legacy_name} без префикса {country}- не читается — "
                    f"переименуйте его в {country}-{base}-d.txt")

    return data_dict
