"""Загрузка свежих котировок с MOEX ISS в папку txt.
Порт проекта download_moex: квартальные фьючерсы — склейка по экспирации,
месячные (NG, BR) — по последнему дню торгов, остальное — дневные свечи."""

import logging
import os
import ssl
from datetime import datetime, timedelta

import pandas as pd
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

NUMERIC_COLS = ['Open', 'High', 'Low', 'Close', 'Volume_lot']


def allow_insecure_ssl() -> None:
    """Обход проблем с сертификатами MOEX; вызывается при загрузке, не при импорте."""
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ.update({'CURL_CA_BUNDLE': '', 'PYTHONHTTPSVERIFY': '0'})
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def create_moex_session() -> requests.Session:
    """HTTP-сессия со стратегией повторов: 429/500/502/503/504, выдержка 1с/2с/4с."""
    session = requests.Session()
    session.trust_env = False
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    retry_strategy = Retry(
        total=config.MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET'],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def get_quarterly_expiry_date(year: int, month_num: int):
    """Дата экспирации квартального фьючерса MOEX — третий четверг месяца."""
    first_day = datetime(year, month_num, 1)
    thursdays = []
    for i in range(31):
        current_day = first_day + timedelta(days=i)
        if current_day.month != month_num:
            break
        if current_day.weekday() == 3:  # четверг
            thursdays.append(current_day)
    return thursdays[2].date()


def fetch_moex_history(ticker: str, session: requests.Session, from_date: str) -> pd.DataFrame:
    """История торгов контракта из архива MOEX ISS (пагинация через start).
    Возвращает DataFrame [Open, High, Low, Close, Volume_lot, Ticker] по датам;
    пустой DataFrame при ошибке или отсутствии данных."""
    url = f'https://moex.com/iss/history/engines/futures/markets/forts/securities/{ticker}.json'
    all_data = []
    start_pointer = 0
    page_count = 0

    try:
        while page_count < config.MAX_PAGES:
            params = {'from': from_date, 'start': start_pointer}
            response = session.get(url, params=params, verify=False, timeout=config.REQUEST_TIMEOUT)
            if response.status_code != 200:
                logging.warning(f"MOEX: HTTP {response.status_code} для {ticker}")
                break

            res = response.json()
            if 'history' not in res or not res['history']['data']:
                break

            columns = res['history']['columns']
            date_idx = columns.index('TRADEDATE')
            open_idx = columns.index('OPEN')
            high_idx = columns.index('HIGH')
            low_idx = columns.index('LOW')
            close_idx = columns.index('CLOSE')
            volume_idx = columns.index('VOLUME')

            page_data = res['history']['data']
            for row in page_data:
                if row[close_idx] is not None:
                    all_data.append([row[date_idx], row[open_idx], row[high_idx],
                                     row[low_idx], row[close_idx], row[volume_idx]])

            start_pointer += len(page_data)
            page_count += 1

            if len(page_data) < config.PAGE_SIZE_THRESHOLD:
                break

    except requests.exceptions.RequestException as e:
        logging.error(f"MOEX: сетевая ошибка при загрузке {ticker}: {e}")
        return pd.DataFrame()
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"MOEX: ошибка парсинга данных {ticker}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"MOEX: непредвиденная ошибка {ticker}: {type(e).__name__}: {e}")
        return pd.DataFrame()

    if page_count >= config.MAX_PAGES:
        logging.warning(f"MOEX: достигнут лимит страниц ({config.MAX_PAGES}) для {ticker}")

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume_lot'])
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df['Ticker'] = ticker
    return df.drop_duplicates(subset=['Date']).set_index('Date').sort_index()


def fetch_stock_history(ticker: str, session: requests.Session, from_date: str) -> pd.DataFrame:
    """Дневные свечи акции/фонда/индекса; для IMOEX — эндпоинт markets/index.

    Формат результата — как в fetch_moex_history.
    """
    clean_ticker = str(ticker).replace('\n', '').replace('\r', '').strip()
    if clean_ticker == 'IMOEX':
        url = f'https://moex.com/iss/engines/stock/markets/index/securities/{clean_ticker}/candles.json'
    else:
        url = f'https://moex.com/iss/engines/stock/markets/shares/securities/{clean_ticker}/candles.json'

    all_data = []
    start = 0
    page_count = 0
    till_date = datetime.now().date().isoformat()

    try:
        while page_count < config.MAX_PAGES:
            params = {'from': from_date, 'till': till_date, 'interval': 24, 'start': start}
            response = session.get(url, params=params, verify=False, timeout=config.REQUEST_TIMEOUT)
            if response.status_code != 200:
                logging.warning(f"MOEX: HTTP {response.status_code} для {clean_ticker}")
                break

            data = response.json()
            if 'candles' not in data or not data['candles']['data']:
                break

            columns = data['candles']['columns']
            rows = data['candles']['data']
            if not rows:
                break

            all_data.extend(rows)
            start += len(rows)
            page_count += 1

    except requests.exceptions.RequestException as e:
        logging.error(f"MOEX: сетевая ошибка при загрузке {clean_ticker}: {e}")
        return pd.DataFrame()
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"MOEX: ошибка парсинга данных {clean_ticker}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"MOEX: непредвиденная ошибка {clean_ticker}: {type(e).__name__}: {e}")
        return pd.DataFrame()

    if page_count >= config.MAX_PAGES:
        logging.warning(f"MOEX: достигнут лимит страниц ({config.MAX_PAGES}) для {clean_ticker}")

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=columns)
    df['Date'] = pd.to_datetime(df['begin']).dt.date
    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                            'close': 'Close', 'volume': 'Volume_lot'})
    df['Ticker'] = clean_ticker
    return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume_lot', 'Ticker']] \
        .drop_duplicates(subset=['Date']).set_index('Date').sort_index()


def _save_txt(df: pd.DataFrame, path: str) -> None:
    """Сохранение непрерывного ряда в txt в формате download_moex (TAB)."""
    df = df.copy()
    df[NUMERIC_COLS] = df[NUMERIC_COLS].round(4)
    df[['Open', 'High', 'Low', 'Close', 'Volume_lot', 'Ticker']].to_csv(
        path, sep='\t', index=True, index_label='Date')


def _download_quarterly(asset: str, session: requests.Session, from_date, output_folder: str, country: str) -> None:
    """Календарная склейка квартального фьючерса: каждый контракт до даты его экспирации."""
    today = datetime.now().date()
    timeline = []
    for year in range(from_date.year, today.year + 1):
        short_digit = str(year)[-1]
        for month_code, month_num in config.QUARTERLY_MONTHS.items():
            timeline.append({
                'api_ticker': f'{asset}{month_code}{short_digit}',
                'expiry_date': get_quarterly_expiry_date(year, month_num),
            })
    timeline.sort(key=lambda x: x['expiry_date'])

    chunks = []
    current_start = from_date
    for contract in timeline:
        end_date = contract['expiry_date']
        if current_start > today:
            continue

        df_single = fetch_moex_history(contract['api_ticker'], session, from_date.isoformat())
        if not df_single.empty:
            df_filtered = df_single[(df_single.index >= current_start) & (df_single.index <= end_date)]
            if not df_filtered.empty:
                chunks.append(df_filtered)
        current_start = end_date + timedelta(days=1)

    if not chunks:
        logging.warning(f"MOEX: нет данных для склейки {asset}")
        return

    continuous = pd.concat(chunks).sort_index()
    continuous.index = pd.to_datetime(continuous.index)
    path = os.path.join(output_folder, f'{country}-{asset}-d.txt')
    _save_txt(continuous, path)
    logging.info(f"MOEX: склейка {asset} завершена — {len(continuous)} строк "
                 f"({continuous.index[0].date()} … {continuous.index[-1].date()}), файл {path}")


def _download_monthly(asset: str, session: requests.Session, from_date, output_folder: str, country: str) -> None:
    """Динамическая склейка месячного товарного фьючерса: каждый контракт до последнего дня его торгов."""
    today = datetime.now().date()
    contracts = []
    for year in range(from_date.year, today.year + 1):
        short_digit = str(year)[-1]
        for month_code in config.MONTHLY_CODES:
            contracts.append(f'{asset}{month_code}{short_digit}')

    pools = []
    for ticker in contracts:
        df_contract = fetch_moex_history(ticker, session, from_date.isoformat())
        if not df_contract.empty:
            pools.append(df_contract)

    if not pools:
        logging.warning(f"MOEX: пропуск {asset}: не удалось получить исторические таблицы")
        return

    pools.sort(key=lambda df: df.index[0])

    chunks = []
    current_start = from_date
    for df_single in pools:
        last_trading_day = df_single.index[-1]
        if current_start > today:
            continue

        df_filtered = df_single[(df_single.index >= current_start) & (df_single.index <= last_trading_day)]
        if not df_filtered.empty:
            chunks.append(df_filtered)
        current_start = last_trading_day + timedelta(days=1)

    if not chunks:
        logging.warning(f"MOEX: нет данных для склейки {asset}")
        return

    continuous = pd.concat(chunks).sort_index()
    continuous.index = pd.to_datetime(continuous.index)
    path = os.path.join(output_folder, f'{country}-{asset}-d.txt')
    _save_txt(continuous, path)
    logging.info(f"MOEX: склейка {asset} завершена — {len(continuous)} строк "
                 f"({continuous.index[0].date()} … {continuous.index[-1].date()}), файл {path}")


def _download_equity(ticker: str, session: requests.Session, from_date, output_folder: str, country: str) -> None:
    """Загрузка дневных свечей акции/фонда/индекса в txt."""
    df_stock = fetch_stock_history(ticker, session, from_date.isoformat())
    if df_stock.empty:
        logging.warning(f"MOEX: нет данных для {ticker}")
        return

    path = os.path.join(output_folder, f'{country}-{ticker}-d.txt')
    _save_txt(df_stock, path)
    logging.info(f"MOEX: {ticker} — {len(df_stock)} строк "
                 f"({df_stock.index[0]} … {df_stock.index[-1]}), файл {path}")


def download_moex_data(txt_folder: str, assets_config: dict, from_date_str: str, country: str) -> None:
    """Загрузка свежих котировок по тикерам из assets_config в txt_folder.
    Классификация — по спискам фьючерсов в config.py; файлы — с префиксом страны (RF-SBER-d.txt).
    Сбой одного тикера не влияет на остальные; прежние файлы при сбое сохраняются."""
    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    logging.info(f"MOEX: загружаю свежие данные (история с {from_date.isoformat()})")
    allow_insecure_ssl()

    session = create_moex_session()
    try:
        for ticker in assets_config:
            try:
                if ticker in config.QUARTERLY_FUTURES:
                    logging.info(f"MOEX: фьючерс {ticker} — календарная склейка квартальных контрактов")
                    _download_quarterly(ticker, session, from_date, txt_folder, country)
                elif ticker in config.MONTHLY_FUTURES:
                    logging.info(f"MOEX: фьючерс {ticker} — динамическая склейка месячных контрактов")
                    _download_monthly(ticker, session, from_date, txt_folder, country)
                else:
                    logging.info(f"MOEX: {ticker} — дневные свечи акции/индекса")
                    _download_equity(ticker, session, from_date, txt_folder, country)
            except Exception as e:
                logging.error(f"MOEX: ошибка загрузки {ticker}: {type(e).__name__}: {e}")
    finally:
        session.close()

    logging.info("MOEX: загрузка завершена")
