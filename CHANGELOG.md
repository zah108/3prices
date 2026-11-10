# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.0] — 2026-11-10

### Added

- **`COUNTRY` parameter** in `config.py`: `'RF'` — Russian market (MOEX), the
  current behavior; `'USA'` — US market (the processing algorithm will be
  described later).
- **US market support** (`COUNTRY = 'USA'`): the asset list
  **`ASSETS_CONFIG_USA`** (US stocks and ETFs: `NVDA`, `AAPL`, …)
  and the downloader **`usa_loader.py`** (a port of the `download_us`
  project): with `DOWNLOAD_USA = True` fresh quotes are fetched from Yahoo
  Finance via `yfinance` — stocks/ETFs as daily OHLCV candles (unadjusted
  `Close`), Yahoo continuous futures (`…=F`) saved under a sanitized name. The
  depth is configurable (`DOWNLOAD_FROM`, common for both markets).

### Changed

- `ASSETS_CONFIG` renamed to **`ASSETS_CONFIG_RF`** (the RF asset list, used
  while `COUNTRY = 'RF'`).
- `main.py` selects the asset list and the download source by `COUNTRY`:
  `'RF'` → `ASSETS_CONFIG_RF` + `DOWNLOAD_MOEX`/`moex_loader.py`, `'USA'` →
  `ASSETS_CONFIG_USA` + `DOWNLOAD_USA`/`usa_loader.py`; an unknown value
  exits with code 1.
- `MOEX_DOWNLOAD_FROM` and `USA_DOWNLOAD_FROM` merged into a single
  **`DOWNLOAD_FROM`** — the download depth of both markets is set in one
  place.
- The title-table continuation pages show no header at all — just the
  continuation of the table.
- Presentation constants (`LEVEL_COLOR`, `BASE_COLORS`, `ROWS_PER_PAGE`,
  `SAT_MIN`, `GREEN_BASE`/`RED_BASE`) moved from `report.py` to `config.py` —
  all configurable parameters now live in one file.
- Quote files in `txt/` and PDF reports now carry the country prefix:
  `txt/RF-SBER-d-5y.txt`, `txt/RF-Si-all-d.txt`,
  `reports/YYYY-MM-DD-3price-RF-N.pdf`. Files without the prefix are no longer
  read (a warning is logged).

## [1.1] — 2026-11-09

### Added

- **Returns page** (page 2 of the report): horizontal bars of the return for every
  ticker over the analysis period, sorted in descending order — profit in green,
  loss in red, the saturation grows with the distance from zero.
- **Return distribution page** (page 3 of the report): tickers grouped into 10
  ranges of 20% each (from `< −80%` to `≥ +80%`), every cell labeled with the
  ticker and its return, with a per-range counter.
- **`№` column** in the title ticker table; with more than 20 tickers the table
  continues onto extra pages instead of overflowing.
- **Built-in MOEX downloader** (`moex_loader.py`, a port of the `download_moex`
  project): with `DOWNLOAD_MOEX = True` in `config.py` fresh quotes are downloaded
  from MOEX ISS into `txt/` before the report is built — quarterly futures spliced
  by expiration, monthly futures spliced by the last trading day, stocks and
  indices fetched as daily candles. The download depth is configurable
  (`MOEX_DOWNLOAD_FROM`).

### Changed

- The analysis period now means exactly `YEARS` calendar years including the
  current one (for `YEARS = 3`: from January 1 of two years back to today).
- The README is bilingual (README_RU.md / README.md) with report samples in
  `docs/`; code comments and docstrings are translated to English.

### Removed

- `txt/`, `logs/` and `reports/` are no longer published in the repository
  (see `.gitignore`).

## [1.0] — 2026-10-18

### Added

- First public release.
- "Three Prices" analysis: for every instrument the current price is classified
  into one of three ranges (low / medium / high) relative to its own min–max
  history over the analysis period.
- PDF report: a title page with the ticker table (current price and colored range
  label) and one chart page per ticker with orange dashed `min / ⅓ / ⅔ / max`
  levels.
- Quotes are read from the `txt/` folder (MOEX exports made with the
  `download_moex` tool).
