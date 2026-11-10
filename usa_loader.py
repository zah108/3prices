"""Загрузка свежих котировок рынка США с Yahoo Finance в txt/.
Порт проекта download_us: акции/ETF — дневные свечи, фьючерсы Yahoo —
склеенный ряд 'ZW-F'. Включается DOWNLOAD_USA; требует пакет yfinance."""

import logging
import os
from datetime import datetime

import pandas as pd
import yfinance as yf


def fetch_yahoo_history(ticker: str, from_date_str: str) -> pd.DataFrame:
    """Дневная история тикера через yfinance (нерегулированная Close).
    Возвращает [Open, High, Low, Close, Volume_lot, Ticker]; пустой DataFrame
    при ошибке или отсутствии данных."""
    clean_ticker = str(ticker).strip()
    try:
        ticker_obj = yf.Ticker(clean_ticker)
        df = ticker_obj.history(
            start=from_date_str,
            interval='1d',
            auto_adjust=False,  # нерегулированные цены Close
        )

        if df.empty:
            return pd.DataFrame()

        df.index = df.index.date
        df['Ticker'] = clean_ticker
        # 'Volume' -> 'Volume_lot': совпадение с txt-форматом moex_loader
        df = df.rename(columns={'Volume': 'Volume_lot'})
        cols = [c for c in ('Open', 'High', 'Low', 'Close', 'Volume_lot') if c in df.columns]
        df = df[cols + ['Ticker']]
        df.index.name = 'Date'

        return df.sort_index()

    except Exception as e:
        logging.error(f"USA: ошибка загрузки {clean_ticker}: {type(e).__name__}: {e}")
        return pd.DataFrame()


NUMERIC_COLS = ['Open', 'High', 'Low', 'Close', 'Volume_lot']


def _save_txt(df: pd.DataFrame, path: str) -> None:
    """Сохранение ряда в txt в формате download_moex (TAB)."""
    df = df.copy()
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].round(4)
    df.to_csv(path, sep='\t', index=True, index_label='Date')


def _download_equity(ticker: str, from_date, output_folder: str, country: str) -> None:
    """Загрузка дневных свечей акции/ETF/индекса в txt."""
    df = fetch_yahoo_history(ticker, from_date.isoformat())
    if df.empty:
        logging.warning(f"USA: нет данных для {ticker}")
        return

    path = os.path.join(output_folder, f'{country}-{ticker}-d-5y.txt')
    _save_txt(df, path)
    logging.info(f"USA: {ticker} — {len(df)} строк "
                 f"({df.index[0]} … {df.index[-1]}), файл {path}")


def _download_future(ticker: str, from_date, output_folder: str, country: str) -> None:
    """Сохранение непрерывного ряда фьючерса Yahoo ('ZW=F' -> файл 'ZW-F')."""
    df = fetch_yahoo_history(ticker, from_date.isoformat())
    if df.empty:
        logging.warning(f"USA: нет данных для {ticker}")
        return

    safe_name = ticker.replace('=F', '-F')
    path = os.path.join(output_folder, f'{country}-{safe_name}-all-d.txt')
    _save_txt(df, path)
    logging.info(f"USA: {ticker} — {len(df)} строк "
                 f"({df.index[0]} … {df.index[-1]}), файл {path}")


def download_usa_data(txt_folder: str, assets_config: dict, from_date_str: str, country: str) -> None:
    """Загрузка свежих котировок США по тикерам из assets_config в txt_folder.

    Сбой одного тикера не влияет на остальные; прежние файлы при сбое сохраняются.
    """
    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    logging.info(f"USA: загружаю свежие данные с Yahoo Finance (история с {from_date.isoformat()})")

    for ticker in assets_config:
        try:
            if str(ticker).endswith('=F'):
                logging.info(f"USA: {ticker} — непрерывный ряд фьючерса Yahoo")
                _download_future(ticker, from_date, txt_folder, country)
            else:
                logging.info(f"USA: {ticker} — дневные свечи акции/ETF")
                _download_equity(ticker, from_date, txt_folder, country)
        except Exception as e:
            logging.error(f"USA: ошибка загрузки {ticker}: {type(e).__name__}: {e}")

    logging.info("USA: загрузка завершена")
