"""Constants and run parameters of the "Three Prices" system."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

# === Config ===
YEARS = 5
TXT_FOLDER = 'txt'
LOGS_FOLDER = 'logs'
REPORTS_FOLDER = 'reports'

# === Downloading data from MOEX ===
# True — download fresh quotes from MOEX ISS before reading txt/
# (download_moex project logic: futures splicing, stock/index candles).
# False — work only with the files in txt/, without the network.
DOWNLOAD_MOEX = False

# Download depth of the MOEX history: files in txt/ are written from this date.
# Keep a margin rather than exactly YEARS years: when YEARS is increased, the
# data for older years must already be in txt/ (the analysis period is cut off
# later by start_date).
MOEX_DOWNLOAD_FROM = '2021-01-01'

ASSETS_CONFIG = {
    'IMOEX': {'name': 'Индекс Московской биржи',    'currency': 'RUB'},
    'SBER':  {'name': 'Акции Сбербанка',            'currency': 'RUB'},
    'GOLD':  {'name': 'Фонд GOLD ETF',                  'currency': 'RUB'},
    'AMNY':  {'name': 'Фонд Атон в юанях ETF',          'currency': 'RUB'},
    'MOEX':  {'name': 'Акции Московской биржи',     'currency': 'RUB'},
    'MTSS':  {'name': 'Акции МТС',                  'currency': 'RUB'},
    'LKOH':  {'name': 'Акции Лукойл',               'currency': 'RUB'},
    'NLMK':  {'name': 'Акции Новолипецкий МК',      'currency': 'RUB'},
    'OZON':  {'name': 'Акции Озон',                 'currency': 'RUB'},
    'PLZL':  {'name': 'Акции Полюс',                'currency': 'RUB'},
    'T':     {'name': 'Акции Т-Технологии',         'currency': 'RUB'},
    'Si':    {'name': 'Фьючерсы Доллар США / Рубль', 'currency': 'RUB'},
    'NG':    {'name': 'Фьючерсы на газ',             'currency': 'USD'},
    'BR':    {'name': 'Фьючерсы на нефть Brent',     'currency': 'USD'},
    'GD':    {'name': 'Фьючерсы на золото',          'currency': 'USD'},
    'SV':    {'name': 'Фьючерсы на серебро',         'currency': 'USD'},
    'PT':    {'name': 'Фьючерсы на платину',         'currency': 'USD'},
    'Ri':    {'name': 'Фьючерсы Ri',                 'currency': 'RUB'},
    'SR':    {'name': 'Фьючерсы Сбербанка',           'currency': 'RUB'},
}


@dataclass(frozen=True)
class RunParams:
    """Run-specific parameters: dates and file names."""

    years: int
    today_str: str
    pdf_filename: str
    log_filename: str
    start_date: pd.Timestamp


def build_run_params() -> RunParams:
    """Compute dates and file names for the current run.

    The start date is January 1 of the year (current − (YEARS − 1)): YEARS
    years in total, including the current one.
    """
    now = datetime.today()
    start_year = now.year - YEARS + 1
    return RunParams(
        years=YEARS,
        today_str=now.strftime('%d.%m.%Y'),
        pdf_filename=f'{now.strftime("%Y-%m-%d")}-3price-{YEARS}.pdf',
        log_filename=f'{now.strftime("%Y-%m")}-3price.log',
        start_date=pd.to_datetime(f'{start_year}-01-01'),
    )
