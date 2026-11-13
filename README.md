<div align="center">

**🇬🇧 English • [🇷🇺 Русский](./README_RU.md)**

</div>

# Three Prices (3price)

**Information generated with this code (its algorithms) is not individual investment advice. Financial decisions are yours alone and at your own risk.**

*The software is provided "as is", without any warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and non-infringement. In no event shall the authors or copyright holders be liable for any loss, damage or other claims arising from the use of this software.*

The code was created with the help of an LLM (Large Language Model) assistant.

![3price](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A financial asset price analysis system: for each instrument the system determines which
of the **three price ranges** its current price falls into, calculates the return
over the period and builds a PDF report with a summary table and charts. The config lists
the tickers and descriptions of the assets of the selected market: the Moscow Exchange
(`COUNTRY = 'RF'`) or the US exchanges (`COUNTRY = 'USA'`).

The code can be used to analyze any financial assets by changing the ticker and its description. The txt folder must contain the data downloaded for these assets (with `DOWNLOAD_MOEX = True`
or `DOWNLOAD_USA = True` the system downloads them itself for the selected market).
Step-by-step instructions — in the section "Adding an asset for download and analysis".

## Table of contents

- [Report samples](#-report-samples)
- [Project layout](#project-layout)
- [Requirements and running](#requirements-and-running)
- [Modules](#modules)
- [Configurable parameters](#configurable-parameters)
- [Adding an asset for download and analysis](#adding-an-asset-for-download-and-analysis)
- [Level-crossing signals (ALERTS)](#level-crossing-signals-alerts)
- [Input data format](#input-data-format)
- [Output files](#output-files)
- [Troubleshooting](#troubleshooting)

## 🖼️ Report samples

<div align="center">
<img src="docs/list-1.jpg" height="200" alt="Report. Page 1">&nbsp;<img src="docs/list-2.jpg" height="200" alt="Report. Page 2">
</div>
<div align="center">
<img src="docs/list-3.jpg" height="200" alt="Report. Page 3">&nbsp;<img src="docs/list-4.jpg" height="200" alt="Report. Page 4">
</div>

The "Three Prices" logic is simple:

1. The closing-price history is taken for the analysis period — exactly `YEARS` calendar years,
   including the current one: from January 1 of the year `(current − (YEARS − 1))` to today.
2. The minimum and maximum price are computed from this history; the `[min … max]` range
   is split into three equal parts by the levels `min + ⅓·range` and `min + ⅔·range`.
3. The current price (the latest available date) is classified:

   | Condition              | Label     | Color in the table |
   |------------------------|-----------|--------------------|
   | price ≤ ⅓ of the range | `низкий` (low) | green          |
   | price ≤ ⅔ of the range | `средний` (medium) | black      |
   | price > ⅔ of the range | `высокий` (high) | red         |

   If the data contain no valid price at all, the label `—` in gray is used.

The idea is a rough but illustrative estimate of how "expensive" an instrument looks
relative to its own multi-year history, with no fundamentals involved.

---

## Project layout

```
3price/
├── main.py           # entry point: orchestration only
├── config.py         # all configurable parameters and the asset list
├── log_setup.py      # logging setup and the startup banner
├── data_loader.py    # reading quotes from txt/ → {ticker: DataFrame}
├── analysis.py       # "three prices" levels and color labels (pure functions)
├── alerts.py         # level-crossing signals from ALERTS_LEVEL
├── report.py         # PDF: title table, returns, distribution, charts
├── moex_loader.py    # downloading fresh quotes from MOEX ISS into txt/ (see DOWNLOAD_MOEX)
├── usa_loader.py     # downloading fresh US quotes from Yahoo Finance into txt/ (see DOWNLOAD_USA)
├── txt/              # INPUT data — quote files (auto-updated with DOWNLOAD_MOEX / DOWNLOAD_USA)
├── logs/             # run logs (created automatically)
├── reports/          # finished PDFs (created automatically)
└── docs/             # illustrations for the README
```

---

## Requirements and running

- Python **3.10+** (the `str | None`, `dict[str, ...]` syntax is used).
- Libraries: `pandas`, `matplotlib`; for downloading data from MOEX — `requests`,
  from Yahoo Finance — `yfinance`:

  ```bash
  pip install pandas matplotlib requests yfinance
  ```

Run from the project folder:

```bash
python3 main.py
```

What happens on start:

1. Run parameters are computed (dates, file names) — see `config.py`.
2. Logging is configured (file + console) and the startup banner is printed.
3. If the download flag of the current country is on (`DOWNLOAD_MOEX` or
   `DOWNLOAD_USA`) — fresh quotes are downloaded into `txt/` (a full MOEX
   download takes ≈2.5 minutes; on failure the previous files are kept).
4. Quotes are read from the `txt/` folder and filtered by the start date.
5. For every ticker the levels and range labels, the return over the
   period and the distribution of tickers over the ranges are computed.
6. The PDF is written into `reports/`; the `logs/` and `reports/` folders are created automatically.

Return codes: `0` — the report is built; `1` — no tickers are left after filtering
(the log gets `[ERROR] Нет данных для сохранения в PDF…` — "No data to save into the PDF").

Console output example (runtime messages are printed in Russian):

```
[INFO] Успешно прочитан файл: RF-SBER-d.txt (729 строк начиная с 2024-01-01)
[ERROR] В файле RF-OZON-d.txt не найдены колонки даты или цены. Доступные: ['foo', 'bar']
[INFO] Проанализировано: 20 тикеров

================================================
[2026-11-13 10:00:00] 🚀 Запуск системы "Три цены" 3price.
================================================
[2026-11-13 10:00:02] ✅ Готово: 2026-11-13-3price-RF-3.pdf — сохранён в папке reports
```

(The log lines are duplicated into the file and the console; their order in the example may differ
due to stdout buffering when the output is redirected.)

---

## Modules

### `main.py` — entry point

The sequence of steps: `build_run_params()` → `setup_logging()` → `write_banner()`
→ the asset list and the download source are chosen by `COUNTRY` (`'RF'` →
`ASSETS_CONFIG_RF` + `DOWNLOAD_MOEX`/`moex_loader`, `'USA'` → `ASSETS_CONFIG_USA`
+ `DOWNLOAD_USA`/`usa_loader`; an unknown value — exit with code 1) → with the download
flag of the current country on — `download_…_data()` → `load_data()`
→ `build_price_maps()` → with empty data an early exit with code 1
→ `generate_pdf()` → the final "Done" line in the log and the console.
The module is safe to import — no code runs on `import main`.

### `config.py` — configuration

All project constants and the asset dictionaries `ASSETS_CONFIG_RF` / `ASSETS_CONFIG_USA`
(chosen by `COUNTRY`). The function
`build_run_params()` assembles `RunParams` (a named bundle of run parameters:
`years`, `today_str`, `pdf_filename`, `log_filename`, `start_date`) and does nothing
else with side effects. The analysis period is exactly `YEARS` calendar years, including
the current one: the start date is computed as `January 1 (current year − (YEARS − 1))`.

### `log_setup.py` — logging

- `setup_logging(logs_folder, log_filename)` — creates the logs folder, sets up
  simultaneous output into a file (UTF-8) and the console, the format `[LEVEL] message`,
  and returns the path to the log file.
- `write_banner(log_path)` — the startup banner «🚀 Запуск системы "Три цены"»
  ("The 'Three Prices' system is starting"), written to the log **without** the standard
  logging prefix.

### `moex_loader.py` — MOEX data download

A port of the `download_moex` project logic. Enabled by the `DOWNLOAD_MOEX` flag in
`config.py`; fresh quotes are written into `txt/` with the country prefix
(`COUNTRY`, e.g. `RF-SBER-d.txt`) and in the same format (TAB:
`Date, Open, High, Low, Close, Volume_lot, Ticker`), after which they are read
by `data_loader` as usual.

- Quarterly futures `Si, CR, Ri, GD, SV, PT, SR, GZ` — "calendar stitching":
  contracts of the form `TICKER + H/M/U/Z + year digit` are downloaded one by one and
  stitched into a continuous series by the expiration dates (the third Thursday of the
  month) → `COUNTRY-TICKER-d.txt` (e.g. `RF-Si-d.txt`).
- Monthly commodity futures `NG, BR` — "dynamic stitching" by the last trading
  day of each contract → `COUNTRY-TICKER-d.txt` (e.g. `RF-BR-d.txt`).
- Stocks, funds and the index — daily candles (`interval=24`); for the `IMOEX`
  index the `markets/index` endpoint is used, for the rest — `markets/shares` →
  `COUNTRY-TICKER-d.txt` (e.g. `RF-SBER-d.txt`).
- Only tickers from `ASSETS_CONFIG_RF` are processed (the "quarterly / monthly /
  stock" classification is set by the lists in `config.py`).
- Reliability: a session with retries on 429/5xx; a failure on one ticker does not
  stop the download of the others; an empty result does not overwrite the file —
  the previous data stay in `txt/`, and the report is built from them.
- The MOEX ISS futures archive lags by about a day (stocks — up to the current
  day, futures — up to the previous trading day). A full download takes ≈2.5 minutes.
- The download depth is `DOWNLOAD_FROM` (common for both markets, default
  `'2021-01-01'`), with a margin relative to `YEARS`: the analysis period is cut off
  later by `start_date`.
- Without the `requests` package the project keeps working with `DOWNLOAD_MOEX = False` —
  the data are then taken from `txt/` as is.

### `usa_loader.py` — US market data download (Yahoo Finance)

A port of the `download_us` project. Enabled by the `DOWNLOAD_USA` flag in
`config.py`, only with `COUNTRY = 'USA'`; quotes are downloaded with the
`yfinance` package from Yahoo Finance and written into `txt/` with the country prefix
and in the same format as the MOEX files — TAB
(`Date, Open, High, Low, Close, Volume_lot, Ticker`),
after which they are read by `data_loader` as usual.

- Assets from `ASSETS_CONFIG_USA`: stocks and ETFs — daily OHLCV candles
  (unadjusted `Close` price) → `COUNTRY-TICKER-d.txt` (e.g.
  `USA-NVDA-d.txt`).
- Yahoo continuous futures (an asset-list key with the `=F` suffix, e.g.
  `'ZW=F'`) are downloaded as is and saved under the sanitized name →
  `COUNTRY-ZW-F-d.txt` (the stitching into a continuous series is done by Yahoo
  itself; in the report the asset is listed as `ZW=F`).
- The download depth is `DOWNLOAD_FROM` (shared with MOEX, default `'2021-01-01'`).
- Reliability: a failure on one ticker does not stop the others; an empty
  result does not overwrite the file — the previous data stay in `txt/`.
- Yahoo Finance must be reachable from your network; without the `yfinance`
  package the project keeps working with `DOWNLOAD_USA = False` — the data are then
  taken from `txt/` as is.

### `data_loader.py` — data loading

- `load_data(txt_folder, assets_config, start_date, country)` — the main function;
  returns `{ticker: DataFrame}` with the columns `begin` (date) and `close` (closing
  price). Only files with the country prefix are read: `COUNTRY-TICKER-d.txt`.
- `_extract_ticker(file_name, country)` — the ticker from the file name: the part between
  the country prefix (`RF-`) and the `-d.txt` suffix
  (e.g. `RF-SBER-d.txt` → `SBER`). For a Yahoo continuous futures
  the original ticker is returned: `USA-ZW-F-d.txt` → `ZW=F`.
- `_parse_price_file(file_path)` — reading one file:
  - the separator is detected automatically (`sep=None, engine='python'`), so
    TAB, comma and semicolon all work;
  - column names are lowercased, angle brackets are removed
    (`<DATE>` → `date`);
  - the date column is looked up among the candidates `begin`, `date`, `timestamp`, `time`;
    the price column — among `close`, `last`, `price`;
  - dates are parsed with `pd.to_datetime`, prices — with `pd.to_numeric`, rows with NaN
    are dropped, the data are sorted by date, prices are rounded to 2 decimal places.

Rules for handling problem files (the system never crashes on one file):

| Situation | Reaction |
| --- | --- |
| The ticker is not in the selected country's asset list | the file is **silently** skipped |
| Date/price columns not found | `[ERROR] … не найдены колонки даты или цены. Доступные: [...]` ("date or price columns not found; available: …") |
| Any other read/parse error | `[ERROR] Ошибка обработки <файл>: <текст>` ("error processing <file>: <text>") |
| Empty after the date filter | `[WARNING] Файл … не содержит данных после …` ("the file … has no data after …") |

For one ticker there is now exactly one file name in `txt/` — `RF-TICKER-d.txt` —
stocks and stitched futures are not distinguished by a suffix. Files without the country
prefix (`SBER-d.txt`, as well as the old names `SBER-d-5y.txt` and
`SBER-all-d.txt`) are not read — a warning with a renaming hint is written to the log.

### `analysis.py` — levels and labels

Pure functions without I/O, easy to cover with tests:

- `compute_levels(df)` → `(min, min+⅓·range, min+⅔·range, max)` — the **only**
  levels formula in the project; both the labels and the dashed chart lines use it.
- `classify_price(current_price, levels)` → `(label, color)` — the rule from the table
  above; the ⅓ and ⅔ boundaries are included into the lower/middle range.
- `build_price_maps(data_dict)` → `(price_level_map, price_color_map)` — labels and
  colors for all tickers at once.

### `alerts.py` — level-crossing signals

`find_signals(data_dict, assets_config, alerts_level, alerts_days)` — returns
the rows of the "Levels" table for all `(ticker, level)` pairs from `alerts_level`:
the date of the freshest level crossing by the closing price over the data period and
the relevance flag (a crossing within the last `alerts_days` calendar
days). A ticker outside the selected country's asset list is skipped silently (levels
may be listed for both markets); a listed ticker without data — with a `[WARNING]`
in the log. Called from `report.py` and only with `ALERTS = True`.

### `report.py` — the PDF report

- `generate_pdf(pdf_path, ...)` — the public entry point: title pages with the ticker
  table, the returns page, the distribution page, then one page per ticker
  **strictly in the order of the selected country's asset list**.
- `_build_table_rows(...)` / `_render_title_pages(...)` — the table
  `№ / Ticker / Name / Current price / Price range`; the text in the last
  column is colored green/black/red/gray by the analysis result. Rows
  are chunked by `ROWS_PER_PAGE = 20`: with more than twenty tickers, the table
  continues on the following pages without the header.
- `_render_levels_pages(...)` / `_build_levels_figure(...)` — the "Levels" table
  after the title pages with `ALERTS = True` (always shown): all `(ticker, level)`
  pairs from `ALERTS_LEVEL` of the selected country, the columns
  `№ / Ticker / Name / Level crossing date / Level price / Current price / Relevance`;
  styled like the title table, centered header, the "Levels" title — only on the
  first page of the section.
- `_render_returns_page(...)` / `_build_returns_figure(...)` — the "Returns by tickers"
  page: horizontal bars for all tickers over the period, sorted
  in descending order; the bar length follows the absolute return, the sign is visible
  in the "+x.x%" label; profit is green, loss — red, the saturation grows
  with the distance from zero (the minimum — `SAT_MIN`).
- `_render_distribution_page(...)` / `_build_distribution_figure(...)` — the "Distribution
  of tickers by return" page: 10 ranges of 20% (from `< −80%` to
  `≥ +80%`), each column holds labeled ticker cells, above the column —
  a counter (`plural_tickers`); the cell color uses the same scale.
- `_render_ticker_chart(...)` — the price chart with a colored line; the levels
  `min, ⅓, ⅔, max` are shown as an orange dashed line (`--`), and the same values
  are highlighted in orange on the Y axis. With `ALERTS = True` the
  `ALERTS_LEVEL` levels are added — gray dashed, their values — gray on the Y axis; distant
  levels do not stretch the scale.
- `plural_years(n)` — the "год/года/лет" (year/years) declension with the 11–14
  exceptions (one function for the whole project — on the title and in the chart titles).
- `plural_tickers(n)` — the "тикер/тикера/тикеров" (ticker) declension (counters on the
  distribution page).
- `_return_color(v, vmax, vmin)` — the single green-red saturation scale for
  the returns and distribution pages.
- `assign_chart_colors(...)` — the line colors are dealt to tickers round-robin from
  `BASE_COLORS` in the asset-list order.

---

## Configurable parameters

All the settable parameters of the project are in one table; they are set only in
`config.py` (run settings, asset lists, signals, style
constants, MOEX download parameters).
Actual values — in the project's `config.py`.

| Parameter | Set in | Default | What it controls |
| --- | --- | --- | --- |
| `YEARS` | `config.py` | `3` | Analysis depth in years: exactly `YEARS` calendar years, including the current one — the period "from January 1 (current year − (YEARS − 1))". Affects data filtering, the title subtitle, the chart titles and the PDF name (`…-3price-RF-N.pdf`). |
| `COUNTRY` | `config.py` | `'RF'` | The market under analysis: `'RF'` — the Russian market (MOEX), `'USA'` — the US market (Yahoo Finance). Also sets the country prefix in the file names: `txt/RF-…` / `txt/USA-…`, `reports/…-3price-RF-N.pdf`. |
| `DOWNLOAD_MOEX` | `config.py` | `True` | `True` — fresh quotes are downloaded from MOEX ISS into `txt/` before the report is built (with `COUNTRY = 'RF'`, see `moex_loader.py`); `False` — work only with the files in `txt/`, offline. |
| `QUARTERLY_FUTURES` | `config.py` | 8 tickers | Quarterly MOEX futures — "calendar stitching" by the expiration dates; a ticker outside the futures lists is downloaded as a stock (see "Adding an asset"). |
| `QUARTERLY_MONTHS` | `config.py` | `H/M/U/Z` → 3/6/9/12 | The month codes of the quarterly contracts and their numbers — the expiration dates are computed from them. |
| `MONTHLY_FUTURES` | `config.py` | 2 tickers | Monthly commodity MOEX futures — "dynamic stitching" by the last trading day of the contract. |
| `MONTHLY_CODES` | `config.py` | `F…Z` (12 codes) | The month codes of the monthly contracts. |
| `REQUEST_TIMEOUT`, `MAX_RETRIES`, `MAX_PAGES`, `PAGE_SIZE_THRESHOLD` | `config.py` | 15 / 3 / 500 / 100 | Network settings of the MOEX ISS download: request timeout (sec), retries on 429/5xx, pagination page limit, page-size threshold. |
| `DOWNLOAD_USA` | `config.py` | `False` | `True` — fresh US quotes are downloaded from Yahoo Finance into `txt/` before the report is built (with `COUNTRY = 'USA'`, see `usa_loader.py`); `False` — work only with the files in `txt/`, offline. |
| `DOWNLOAD_FROM` | `config.py` | `'2021-01-01'` | Download depth, shared by both markets (MOEX and Yahoo Finance): the files in `txt/` are written from this date. Keep a margin relative to `YEARS` — the analysis period is cut off later by `start_date`. |
| `TXT_FOLDER` | `config.py` | `'txt'` | Folder with the input quote files. |
| `LOGS_FOLDER` | `config.py` | `'logs'` | Folder for logs (created automatically). |
| `REPORTS_FOLDER` | `config.py` | `'reports'` | Folder for PDF reports (created automatically). |
| `ASSETS_CONFIG_RF` | `config.py` | 20 tickers | The RF asset list, used with `COUNTRY = 'RF'` — see below. |
| `ASSETS_CONFIG_USA` | `config.py` | 28 tickers | The US asset list, used with `COUNTRY = 'USA'` — see below. |
| `ALERTS` | `config.py` | `True` | The level-crossing signals switch: `True` — search for `ALERTS_LEVEL` crossings, show the "Levels" table after the title and draw the levels on the charts; `False` — the feature is off, the report is as before. |
| `ALERTS_DAYS` | `config.py` | `10` | The signal search window, calendar days from the ticker's latest data date. |
| `ALERTS_LEVEL` | `config.py` | — | Price levels to track: `{ticker: [level, …]}`, the tickers — from the selected country's asset list. A level crossed by the closing price is a signal (see "Level-crossing signals"). |
| `ALERTS_LEVEL_COLOR` | `config.py` | `'gray'` | The color of the `ALERTS_LEVEL` levels on the ticker charts (dashed lines and Y-axis ticks). |
| `LEVEL_COLOR` | `config.py` | `'#ff7f0e'` | The orange color of the dashed levels and their Y-axis labels. |
| `BASE_COLORS` | `config.py` | 10 colors | The palette of the chart line colors; with more tickers the colors repeat round-robin. |
| `ROWS_PER_PAGE` | `config.py` | `20` | Data rows of the ticker table per title page (the rest continues on the next page). |
| `SAT_MIN` | `config.py` | `0.35` | The minimum color saturation on the returns and distribution pages: at zero the color is pale but distinguishable. |
| `GREEN_BASE`, `RED_BASE` | `config.py` | `#2ca02c` / `#d62728` | The base green/red colors of the return scale. |

### The asset lists `ASSETS_CONFIG_RF` / `ASSETS_CONFIG_USA`

Both lists are dictionaries of the same shape; the one selected by `COUNTRY` gets into the report:

```python
'SBER': {'name': 'Акции Сбербанка', 'currency': 'RUB'},
'NG':   {'name': 'Фьючерсы на газ', 'currency': 'USD'},
```

- The key is the **ticker**, which must exactly match the ticker part of the
  file name in `txt/` — between the country prefix (`RF-` / `USA-`) and the
  `-d.txt` suffix (case matters: `Si` ≠ `SI`).
- `name` — the human-readable name for the table and the chart titles.
- `currency` — the Y-axis label of the chart (`Цена (RUB)` / `Цена (USD)` — "Price"). Currency
  conversion is **not performed**: the `NG`, `BR`, `GD`, `SV`, `PT` futures are shown
  in dollars, as they are in the data.

**How to add an asset** — step by step in the "Adding an asset for download
and analysis" section below. To remove an asset from the report — delete its row
from the dictionary (the file in `txt/` is simply ignored afterwards).

### The order of assets in the report

**The order of assets (sorting).** The order of the dictionary keys is the only
determinant; no automatic sorting (alphabetical, by return, etc.) is performed. It controls:

- the order of the table rows on the title page;
- the order of the chart pages (one per asset);
- the round-robin dealing of the `BASE_COLORS` line colors.

To change the order — rearrange the rows of the dictionary in `config.py`. Two
report pages are sorted on their own: "Returns by tickers" — by the return value
(descending), "Distribution of tickers by return" — by ranges.

### What is computed automatically (not configurable)

- `start_date` — January 1 of the year `(current − (YEARS − 1))`;
- the PDF name — `YYYY-MM-DD-3price-RF-N.pdf` (with the `COUNTRY` prefix) by the launch date;
- the log name — `YYYY-MM-3price.log` by the launch month;
- the range label colors (green/black/red/gray) — hard-coded in
  `analysis.classify_price`; the green-red return scale — in `_return_color`
  from the base `GREEN_BASE`/`RED_BASE` (set in `config.py`).

---

## Adding an asset for download and analysis

For a new asset to appear in the report, two steps are enough; for MOEX
futures a third one is also needed.

**Step 1. Add a row to the asset list** (`config.py`) — into the dictionary
of the selected market: `ASSETS_CONFIG_RF` with `COUNTRY = 'RF'` or
`ASSETS_CONFIG_USA` with `COUNTRY = 'USA'`:

```python
'LKOH': {'name': 'Акции Лукойл', 'currency': 'RUB'},
```

- the key is the **data source ticker**: the MOEX ticker for the Russian market, the Yahoo
  ticker for the US market; it is also the ticker part of the file name in `txt/` (case
  matters: `Si` ≠ `SI`);
- `name` — the name in the table and the chart titles;
- `currency` — the Y-axis label of the chart; currency conversion is not performed;
- the row's position in the dictionary — the asset's order in the report (see "The order
  of assets").

**Step 2. Provide the data in `txt/`.** With the download of the selected
market enabled (`DOWNLOAD_MOEX = True` / `DOWNLOAD_USA = True`) the quote file
is created and updated by itself at the next run. In manual mode
put a file with this name there yourself — the format requirements are in the "Input
data format" section. The file name: `COUNTRY-TICKER-d.txt` — both for
stocks/funds/indexes and for stitched futures.
A ticker without a file does not get into the report — the file is looked up strictly by name.

**Step 3. Only for MOEX futures — a peculiarity.** The download method is chosen by
`moex_loader.py` from the lists in `config.py`, not from the asset dictionary: everything that did not
get into the futures lists is considered a stock/fund/index and downloaded
as daily stock-market candles.

- quarterly futures — the `QUARTERLY_FUTURES` list (`Si, CR, Ri, GD, SV,
  PT, SR, GZ`): "calendar stitching" of the contracts
  `TICKER+H/M/U/Z+year digit` by the expiration dates → `RF-TICKER-d.txt`;
- monthly commodity futures — the `MONTHLY_FUTURES` list (`NG, BR`): "dynamic
  stitching" by the last trading day of each contract → `RF-TICKER-d.txt`;
- everything else — daily candles → `RF-TICKER-d.txt`.

Therefore a new MOEX futures is added in **two places**: a row in
`ASSETS_CONFIG_RF` and the ticker code — into `QUARTERLY_FUTURES` or
`MONTHLY_FUTURES` in `config.py`. If only the asset dictionary is edited,
the loader goes to the stock market for candles, returns an empty result
(`[WARNING] MOEX: нет данных для …` in the log) and the file is not created in `txt/` —
the ticker does not appear in the report.

**A US-market futures** (a Yahoo continuous contract) is set by a key with the
`=F` suffix, e.g. `'ZW=F'`; the file is saved under the sanitized name
`USA-ZW-F-d.txt`, and in the report the asset is listed as `ZW=F`. Nothing
else needs to be entered — the "futures or stock" choice is made by the `=F`
suffix in the key.

**Levels for the signals** (optional): for the crossings to be searched for the new
asset, add it to `ALERTS_LEVEL` — see "Level-crossing
signals".

---

## Level-crossing signals (ALERTS)

With `ALERTS = True` the system tracks the price levels from `ALERTS_LEVEL` —
a dictionary of the form `{ticker: [level, ...]}`:

```python
ALERTS_LEVEL = {
    'SBER': [280.0, 320.0],   # one ticker — several levels
    'NG':   [4.0],
}
```

- A signal is the crossing of a level by the **closing price** upward or downward;
  touching the level (closing exactly at the level) also counts as a signal.
- For each `(ticker, level)` pair the freshest crossing over the data period is taken —
  its date goes into the "Level crossing date" column
  (the data are daily; the time will appear automatically if it is present in the data).
- "Relevance" — `Да` ("Yes") if the freshest crossing happened within the last
  `ALERTS_DAYS` calendar days from the ticker's latest data date, otherwise `Нет`
  ("No"; `Да` is printed in green); a level never crossed by the price over the period
  gets `—` as the date and `Нет`.
- Only the `ALERTS_LEVEL` tickers that are part of the selected country's asset list
  (`COUNTRY`) are taken into account; the tickers of the other market are skipped silently,
  a listed ticker without data — with a `[WARNING]` in the log.

What changes in the report (only with `ALERTS = True`):

- after the title table the **"Levels"** table is always shown (styled
  like the title table, centered header) with rows for all tickers from
  `ALERTS_LEVEL` of the selected country and the columns `№ / Ticker / Name /
  Level crossing date / Level price / Current price / Relevance`;
- at the bottom of the "Levels" page a note is printed: a level counts as relevant
  if the crossing happened within the last `ALERTS_DAYS` days — the number
  is substituted from `config.py`; when the table spans several pages,
  the note is printed only on the last one;
- on the ticker charts the `ALERTS_LEVEL` levels are drawn as a gray dashed line, their
  values are highlighted in gray on the Y axis (in the style of the `min / ⅓ / ⅔ / max`
  levels); levels far from the price range do not stretch the chart scale.

With `ALERTS = False` there are no signals: the report is built as before — no
"Levels" table and no levels on the charts.

---

## Input data format

The file name in `txt/`: `RF-TICKER-d.txt` for the Russian market and
`USA-TICKER-d.txt` for the US market (the prefix = the `COUNTRY` value). The
`-d.txt` suffix is the same for all asset types — stocks, funds, indexes and stitched
futures (the Yahoo continuous futures `ZW=F` is saved as `USA-ZW-F-d.txt`).

Both loaders write the same format — a tab-separated text CSV:

```
Date Open High Low Close Volume_lot Ticker
2026-11-02 342.67 343.8 335.82 338.32 64757700 AAPL
```

With `DOWNLOAD_MOEX = True` (MOEX ISS) or `DOWNLOAD_USA = True` (Yahoo Finance)
the files are updated automatically. In manual mode a text CSV with
any separator and two mandatory columns is enough — the date and the closing price
(the candidates are listed in the `data_loader.py` description); the other columns
(`Open`, `High`, …, `Ticker`) are allowed and ignored.

Content requirements:

- dates — in any format understood by `pandas.to_datetime` (`2020-01-06`,
  `06.01.2020`, `20200106` etc.);
- prices — numbers; rows with empty/non-numeric values are dropped;
- data from `start_date` on are enough — everything earlier is filtered out, but if after
  the filter not a single row remains, the ticker does not get into the report
  (a `[WARNING]` in the log);
- data before `start_date` in the file do not interfere — they are cut off at load.

The data files can be downloaded by the `download_moex` program (RF) and copied into the
`txt` folder — or the download can be left to the system itself (`DOWNLOAD_MOEX = True` /
`DOWNLOAD_USA = True`).

## Output files

### `reports/YYYY-MM-DD-3price-RF-N.pdf`

- Page 1 — the title: the header with the date, the subtitle "Analysis over N years (from …)",
  the table `№ / Ticker / Name / Current price / Price range` with the colored
  range label. With more than 20 tickers the table continues on the following
  pages (without the header).
- Only with `ALERTS = True` — the "Levels" table for all `(ticker —
  level)` pairs from `ALERTS_LEVEL` of the selected country: the date of the latest crossing,
  the current price and "Relevance" (`Да` — a crossing within the last
  `ALERTS_DAYS` days, otherwise `Нет`); inserted right after the title, so
  the numbering of the following pages shifts. See "Level-crossing
  signals".
- Page 2 — "Returns by tickers": horizontal bars for all tickers
  over the period (descending sort; profit — green, loss — red;
  the saturation grows with the distance from zero), "+x.x%" labels at the bars.
- Page 3 — "Distribution of tickers by return": 10 ranges of 20%
  (from `< −80%` to `≥ +80%`), each column holds labeled ticker cells,
  above the column a ticker counter.
- Then one page per ticker (in the order of the selected country's asset list): the price chart over
  the period with the orange dashed levels `min / ⅓ / ⅔ / max`; with
  `ALERTS = True` the chart additionally shows the `ALERTS_LEVEL` levels — gray
  dashed.

### `logs/YYYY-MM-3price.log`

The full journal of the month's runs: the launch banners, the file reading lines
(how many rows were read and from what date), errors and warnings, the final
"✅ Готово" ("Done") line. The log is appended on every run.

---

## Troubleshooting

| Symptom | Cause and what to do |
| --- | --- |
| `[ERROR] Нет данных для сохранения в PDF` ("No data to save into the PDF", return code 1) | There are no files in `txt/` with tickers from the selected country's asset list, or the folders cannot be created — check that you run from the project folder and the file names match the tickers. |
| `MOEX: … сетевая ошибка / HTTP …` ("network error") during the download | MOEX ISS connection problems: the already downloaded files in `txt/` are kept and the report is built from them — rerun later. The download is enabled by the `DOWNLOAD_MOEX = True` flag. |
| `USA: … нет данных / ошибка загрузки` ("no data / download error") during the download | Yahoo Finance is unreachable from your network (timeout/blocking) or the ticker is wrong: the already downloaded files in `txt/` are kept and the report is built from them — rerun later. The download is enabled by the `DOWNLOAD_USA = True` flag with `COUNTRY = 'USA'`. |
| `…не найдены колонки даты или цены. Доступные: ['foo', 'bar']` ("date or price columns not found") | The file has no column with an expected name — rename the column (`<DATE>`/`<CLOSE>` etc.) or add your candidate to the `_parse_price_file` list in `data_loader.py`. |
| `Файл … не содержит данных после YYYY-MM-DD` ("the file has no data after …") | The file has no quotes for the analysis period — download a longer history. |
| The ticker is in `txt/` but did not appear in the report | The ticker is not in the asset list, or the name/case does not match (`Si` ≠ `SI`), or the file name is not of the `COUNTRY-TICKER-d.txt` form. |
| A new MOEX futures did not appear in the report / `MOEX: нет данных для …` | The futures code was added only to the asset list but not to `QUARTERLY_FUTURES` / `MONTHLY_FUTURES` in `config.py` — the loader looks for it among stocks (see "Adding an asset for download and analysis"). |
| `ALERTS_LEVEL: по тикеру … нет данных — пропущен` ("no data for the ticker — skipped") | `ALERTS_LEVEL` lists a ticker from the selected country's asset list that has no file in `txt/` — check the file presence and name (case matters). |
| `ModuleNotFoundError: pandas` | Wrong interpreter: the libraries are installed into a specific Python (`/usr/local/bin/python3.12` on the author's machine). |
| `ModuleNotFoundError: requests` | The `requests` package is not installed while `DOWNLOAD_MOEX = True`: install it (`pip install requests`) or turn the download off (`DOWNLOAD_MOEX = False`). |
| `ModuleNotFoundError: yfinance` | The `yfinance` package is not installed while `DOWNLOAD_USA = True`: install it (`pip install yfinance`) or turn the download off (`DOWNLOAD_USA = False`). |
