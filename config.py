"""Константы и параметры запуска системы «Три цены»."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

# === Настройки ===
YEARS = 3

# Страна анализа: 'RF' — российский рынок (MOEX); 'USA' — рынок США.
COUNTRY = 'RF'

TXT_FOLDER = 'txt'
LOGS_FOLDER = 'logs'
REPORTS_FOLDER = 'reports'

# Глубина выгрузки, общая для обоих рынков (MOEX и Yahoo Finance): файлы в
# txt/ пишутся от этой даты. Держите запас относительно YEARS.
DOWNLOAD_FROM = '2021-01-01'

# === Загрузка данных с MOEX (используется moex_loader.py) ===
# True — перед чтением txt/ скачать свежие котировки с MOEX ISS (логика
# download_moex). False — работать только с файлами в txt/, без сети.
DOWNLOAD_MOEX = True

# Классификация инструментов (как в download_moex): тикеры из QUARTERLY_FUTURES
# склеиваются по датам экспирации, из MONTHLY_FUTURES — по последнему дню
# торгов, остальные качаются как дневные свечи.
QUARTERLY_FUTURES = ('Si', 'CR', 'Ri', 'GD', 'SV', 'PT', 'SR', 'GZ')
QUARTERLY_MONTHS = {'H': 3, 'M': 6, 'U': 9, 'Z': 12}  # код месяца контракта → его номер
MONTHLY_FUTURES = ('NG', 'BR')
MONTHLY_CODES = ('F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z')

# Сетевые настройки загрузки MOEX ISS.
REQUEST_TIMEOUT = 15       # секунд на один запрос
MAX_RETRIES = 3            # повторы при 429/5xx и сетевых сбоях
MAX_PAGES = 500            # лимит страниц пагинации (защита от зацикливания)
PAGE_SIZE_THRESHOLD = 100  # порог размера страницы для остановки пагинации

# === Загрузка данных рынка США (Yahoo Finance, usa_loader.py) ===
# True — перед чтением txt/ скачать свежие котировки США через yfinance
# (только при COUNTRY = 'USA'). False — работать только с файлами в txt/.
DOWNLOAD_USA = False

# Список активов RF (используется при COUNTRY = 'RF').
ASSETS_CONFIG_RF = {
    'IMOEX': {'name': 'Индекс Московской биржи',    'currency': 'RUB'},
    'SBER':  {'name': 'Акции Сбербанка',            'currency': 'RUB'},
    'GOLD':  {'name': 'Фонд GOLD ETF',              'currency': 'RUB'},
    'AMNY':  {'name': 'Фонд Атон в юанях ETF',      'currency': 'RUB'},
    'MOEX':  {'name': 'Акции Московской биржи',     'currency': 'RUB'},
    'MTSS':  {'name': 'Акции МТС',                  'currency': 'RUB'},
    'LKOH':  {'name': 'Акции Лукойл',               'currency': 'RUB'},
    'NLMK':  {'name': 'Акции Новолипецкий МК',      'currency': 'RUB'},
    'OZON':  {'name': 'Акции Озон',                 'currency': 'RUB'},
    'ALRS':  {'name': 'Акции Алроса',               'currency': 'RUB'},
    'Si':    {'name': 'Фьючерсы Доллар США / Рубль','currency': 'RUB'},
    'CR':    {'name': 'Фьючерсы Юань / Рубль',      'currency': 'RUB'},
    'NG':    {'name': 'Фьючерсы на газ',            'currency': 'USD'},
    'BR':    {'name': 'Фьючерсы на нефть Brent',    'currency': 'USD'},
    'GD':    {'name': 'Фьючерсы на золото',         'currency': 'USD'},
    'SV':    {'name': 'Фьючерсы на серебро',        'currency': 'USD'},
    'PT':    {'name': 'Фьючерсы на платину',        'currency': 'USD'},
    'Ri':    {'name': 'Фьючерсы Ri',                'currency': 'RUB'},
    'SR':    {'name': 'Фьючерсы Сбербанка',         'currency': 'RUB'},
    'GZ':    {'name': 'Фьючерсы Газпрома',         'currency': 'RUB'},
}

# Список активов США для COUNTRY = 'USA' (тикеры Yahoo Finance; фьючерсы
# Yahoo несут суффикс '…=F', например 'ZW=F').
ASSETS_CONFIG_USA = {
    'NVDA': {'name': 'Shares - NVIDIA Corporation',              'currency': 'USD'},
    
    'CCL':  {'name': 'Shares - Carnival Corporation Ltd.',       'currency': 'USD'},
    'T':    {'name': 'Shares - AT&T Inc.',                       'currency': 'USD'},
    'F':    {'name': 'Shares - Ford Motor Company',              'currency': 'USD'},
    'AMD':  {'name': 'Shares - Advanced Micro Devices, Inc.',    'currency': 'USD'},
    'AAPL': {'name': 'Shares - Apple Inc.',                      'currency': 'USD'},
    'QCOM': {'name': 'Shares - QUALCOMM Incorporated',           'currency': 'USD'},
    'PLTR': {'name': 'Shares - Palantir Technologies Inc.',      'currency': 'USD'},
    'RCL':  {'name': 'Shares - Royal Caribbean Cruises Ltd.',    'currency': 'USD'},
    'SBUX': {'name': 'Shares - Starbucks Corporation',           'currency': 'USD'},
    'JNJ':  {'name': 'Shares - Johnson & Johnson',               'currency': 'USD'},
    'MA':   {'name': 'Shares - Mastercard Incorporated',         'currency': 'USD'},
    'MSFT': {'name': 'Shares - Microsoft Corp',                  'currency': 'USD'},
    'META': {'name': 'Shares - Meta Platforms Inc',              'currency': 'USD'},
    'WMT':  {'name': 'Shares - Walmart Inc',                     'currency': 'USD'},
    'JPM':  {'name': 'Shares - JPMorgan Chase & Co',             'currency': 'USD'},
    'V':    {'name': 'Shares - Visa Inc',                        'currency': 'USD'},
    'XOM':  {'name': 'Shares - ExxonMobil Holdings Corp',        'currency': 'USD'},
    'ABBV': {'name': 'Shares - Abbvie Inc',                      'currency': 'USD'},
    'PG':   {'name': 'Shares - Procter & Gamble Co',             'currency': 'USD'},
    'CSCO': {'name': 'Shares - Cisco Systems Inc',               'currency': 'USD'},
    'UNG':  {'name': 'ETF - United States Natural Gas Fund',     'currency': 'USD'},
    'PPLT': {'name': 'ETF - abrdn Physical Platinum Shares ETF', 'currency': 'USD'},
    'URA':  {'name': 'ETF - Global X Uranium ETF',               'currency': 'USD'},
    'BNO':  {'name': 'ETF - United States Brent Oil Fund, LP',   'currency': 'USD'},
    'SLV':  {'name': 'ETF - iShares Silver Trust',               'currency': 'USD'},
    'BITO': {'name': 'ETF - ProShares Bitcoin ETF',              'currency': 'USD'},
    'COPX': {'name': 'ETF - Global X Copper Miners ETF',         'currency': 'USD'},
        
}

# === Сигналы пересечения уровней (alerts.py, report.py) ===
ALERTS = True   # True — искать пересечения уровней и выводить таблицу «Уровни»
ALERTS_DAYS = 10  # окно поиска сигналов, календарных дней от последней даты данных

# Уровни цены для отслеживания: {тикер из списка активов страны: [уровень, ...]}.
# Пересечение уровня ценой close снизу вверх или сверху вниз — сигнал.
ALERTS_LEVEL = {
    'SBER': [300.0, 325.0],
    'LKOH': [7000.0],
    'GOLD': [3.1250],
    'SV': [70.0],
    'NG':   [3.5, 4.0],
    'UNG':   [10.0, 12.0],
}

# Цвет уровней ALERTS_LEVEL на графиках тикеров (в стиле уровней min/max).
ALERTS_LEVEL_COLOR = 'gray'

# === Оформление отчёта (используется report.py) ===
LEVEL_COLOR = '#ff7f0e'   # цвет пунктирных уровней и их подписей на оси Y
BASE_COLORS = ['#1f77b4', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
               '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#ff7f0e']  # палитра линий
ROWS_PER_PAGE = 20        # строк данных таблицы тикеров на одной титульной странице
SAT_MIN = 0.35            # минимальная насыщенность цвета на страницах доходности
GREEN_BASE = (0.173, 0.627, 0.173)  # #2ca02c — базовый зелёный шкалы доходности
RED_BASE = (0.839, 0.153, 0.153)    # #d62728 — базовый красный шкалы доходности


@dataclass(frozen=True)
class RunParams:
    """Параметры конкретного запуска: даты и имена файлов."""

    years: int
    today_str: str
    pdf_filename: str
    log_filename: str
    start_date: pd.Timestamp


def build_run_params() -> RunParams:
    """Расчёт дат и имён файлов для текущего запуска: период — YEARS лет
    (включая текущий), от 1 января года (текущий − (YEARS − 1))."""
    now = datetime.today()
    start_year = now.year - YEARS + 1
    return RunParams(
        years=YEARS,
        today_str=now.strftime('%d.%m.%Y'),
        pdf_filename=f'{now.strftime("%Y-%m-%d")}-3price-{COUNTRY}-{YEARS}.pdf',
        log_filename=f'{now.strftime("%Y-%m")}-3price.log',
        start_date=pd.to_datetime(f'{start_year}-01-01'),
    )
