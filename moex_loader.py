"""Downloading fresh quotes from MOEX ISS into the txt folder.

A port of the download_moex project logic (download_moex-1d-12.py):

- quarterly futures (Si, Ri, GD, SV, PT, SR, CR) are downloaded contract by
  contract and spliced into a continuous series by expiration dates (the third
  Thursday of the month);
- monthly commodity futures (NG, BR) are spliced by the last trading day of
  each contract;
- stocks, funds and the index (IMOEX) are fetched as daily candles.

Files are written into txt/ under the same names and in the same format
(TAB: Date, Open, High, Low, Close, Volume_lot, Ticker), so data_loader.load_data()
reads them without any changes.

Enabled by the DOWNLOAD_MOEX constant in config.py. A failure on one ticker
does not stop the others; if the network is down, the previous files stay in
txt/ and the report is built from them.
"""

import logging
import os
import ssl
from datetime import datetime, timedelta

import pandas as pd
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# === Instrument classification (as in download_moex) ===
QUARTERLY_FUTURES = ('Si', 'CR', 'Ri', 'GD', 'SV', 'PT', 'SR')
QUARTERLY_MONTHS = {'H': 3, 'M': 6, 'U': 9, 'Z': 12}
MONTHLY_FUTURES = ('NG', 'BR')
MONTHLY_CODES = ('F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z')

# === Network settings (as in download_moex) ===
REQUEST_TIMEOUT = 15       # seconds per request
MAX_RETRIES = 3            # retries on 429/5xx and network failures
MAX_PAGES = 500            # pagination page limit (loop protection)
PAGE_SIZE_THRESHOLD = 100  # page size threshold to stop pagination

NUMERIC_COLS = ['Open', 'High', 'Low', 'Close', 'Volume_lot']


def allow_insecure_ssl() -> None:
    """Work around the MOEX certificate problems — as in download_moex.

    Called at download time, not at module import.
    """
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ.update({'CURL_CA_BUNDLE': '', 'PYTHONHTTPSVERIFY': '0'})
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def create_moex_session() -> requests.Session:
    """HTTP session with a retry strategy: 429/500/502/503/504, 1s/2s/4s backoff."""
    session = requests.Session()
    session.trust_env = False
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    retry_strategy = Retry(
        total=MAX_RETRIES,
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
    """MOEX quarterly futures expiration date — the third Thursday of the month."""
    first_day = datetime(year, month_num, 1)
    thursdays = []
    for i in range(31):
        current_day = first_day + timedelta(days=i)
        if current_day.month != month_num:
            break
        if current_day.weekday() == 3:  # Thursday
            thursdays.append(current_day)
    return thursdays[2].date()


def fetch_moex_history(ticker: str, session: requests.Session, from_date: str) -> pd.DataFrame:
    """Futures contract trading history from the eternal MOEX ISS archive.

    Pagination via the start parameter, loop protection — MAX_PAGES.
    Returns a DataFrame [Open, High, Low, Close, Volume_lot, Ticker]
    indexed by date; an empty DataFrame on error or when there is no data.
    """
    url = f'https://moex.com/iss/history/engines/futures/markets/forts/securities/{ticker}.json'
    all_data = []
    start_pointer = 0
    page_count = 0

    try:
        while page_count < MAX_PAGES:
            params = {'from': from_date, 'start': start_pointer}
            response = session.get(url, params=params, verify=False, timeout=REQUEST_TIMEOUT)
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

            if len(page_data) < PAGE_SIZE_THRESHOLD:
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

    if page_count >= MAX_PAGES:
        logging.warning(f"MOEX: достигнут лимит страниц ({MAX_PAGES}) для {ticker}")

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume_lot'])
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df['Ticker'] = ticker
    return df.drop_duplicates(subset=['Date']).set_index('Date').sort_index()


def fetch_stock_history(ticker: str, session: requests.Session, from_date: str) -> pd.DataFrame:
    """Daily candles of a stock, fund or index via MOEX ISS.

    For indexes (IMOEX) the markets/index endpoint is used, otherwise
    markets/shares. The result format is the same as in fetch_moex_history.
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
        while page_count < MAX_PAGES:
            params = {'from': from_date, 'till': till_date, 'interval': 24, 'start': start}
            response = session.get(url, params=params, verify=False, timeout=REQUEST_TIMEOUT)
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

    if page_count >= MAX_PAGES:
        logging.warning(f"MOEX: достигнут лимит страниц ({MAX_PAGES}) для {clean_ticker}")

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
    """Save the continuous series to txt in the download_moex format (TAB)."""
    df = df.copy()
    df[NUMERIC_COLS] = df[NUMERIC_COLS].round(4)
    df[['Open', 'High', 'Low', 'Close', 'Volume_lot', 'Ticker']].to_csv(
        path, sep='\t', index=True, index_label='Date')


def _download_quarterly(asset: str, session: requests.Session, from_date, output_folder: str) -> None:
    """Calendar splicing of a quarterly futures contract: each contract until its expiration date."""
    today = datetime.now().date()
    timeline = []
    for year in range(from_date.year, today.year + 1):
        short_digit = str(year)[-1]
        for month_code, month_num in QUARTERLY_MONTHS.items():
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
    path = os.path.join(output_folder, f'{asset}-all-d.txt')
    _save_txt(continuous, path)
    logging.info(f"MOEX: склейка {asset} завершена — {len(continuous)} строк "
                 f"({continuous.index[0].date()} … {continuous.index[-1].date()}), файл {path}")


def _download_monthly(asset: str, session: requests.Session, from_date, output_folder: str) -> None:
    """Dynamic splicing of a monthly commodity futures contract: each contract until its last trading day."""
    today = datetime.now().date()
    contracts = []
    for year in range(from_date.year, today.year + 1):
        short_digit = str(year)[-1]
        for month_code in MONTHLY_CODES:
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
    path = os.path.join(output_folder, f'{asset}-all-d.txt')
    _save_txt(continuous, path)
    logging.info(f"MOEX: склейка {asset} завершена — {len(continuous)} строк "
                 f"({continuous.index[0].date()} … {continuous.index[-1].date()}), файл {path}")


def _download_equity(ticker: str, session: requests.Session, from_date, output_folder: str) -> None:
    """Download daily candles of a stock/fund/index into txt."""
    df_stock = fetch_stock_history(ticker, session, from_date.isoformat())
    if df_stock.empty:
        logging.warning(f"MOEX: нет данных для {ticker}")
        return

    path = os.path.join(output_folder, f'{ticker}-d-5y.txt')
    _save_txt(df_stock, path)
    logging.info(f"MOEX: {ticker} — {len(df_stock)} строк "
                 f"({df_stock.index[0]} … {df_stock.index[-1]}), файл {path}")


def download_moex_data(txt_folder: str, assets_config: dict, from_date_str: str) -> None:
    """Download fresh quotes for the tickers from assets_config into txt_folder.

    Classification as in download_moex: quarterly futures — calendar splicing,
    NG/BR — dynamic splicing, the rest — daily stock/index candles.
    Files are overwritten in the same format; a failure on one ticker does not
    affect the others, and on a total failure the previous files in txt/ are
    kept.
    """
    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    logging.info(f"MOEX: загружаю свежие данные (история с {from_date.isoformat()})")
    allow_insecure_ssl()

    session = create_moex_session()
    try:
        for ticker in assets_config:
            try:
                if ticker in QUARTERLY_FUTURES:
                    logging.info(f"MOEX: фьючерс {ticker} — календарная склейка квартальных контрактов")
                    _download_quarterly(ticker, session, from_date, txt_folder)
                elif ticker in MONTHLY_FUTURES:
                    logging.info(f"MOEX: фьючерс {ticker} — динамическая склейка месячных контрактов")
                    _download_monthly(ticker, session, from_date, txt_folder)
                else:
                    logging.info(f"MOEX: {ticker} — дневные свечи акции/индекса")
                    _download_equity(ticker, session, from_date, txt_folder)
            except Exception as e:
                logging.error(f"MOEX: ошибка загрузки {ticker}: {type(e).__name__}: {e}")
    finally:
        session.close()

    logging.info("MOEX: загрузка завершена")
