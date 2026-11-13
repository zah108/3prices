"""Поиск сигналов пересечения ценовых уровней из ALERTS_LEVEL."""

import logging

import pandas as pd


def find_signals(data_dict: dict, assets_config: dict, alerts_level: dict,
                 alerts_days: int) -> list[dict]:
    """Строки таблицы «Уровни» по всем парам «тикер, уровень» из alerts_level
    (учитываются только тикеры списка активов выбранной страны). Дата — самое
    свежее пересечение за период данных; actual — сигнал в окне alerts_days."""
    signals: list[dict] = []
    for ticker, levels in alerts_level.items():
        if ticker not in assets_config:
            continue  # тикер другого рынка — пропускаем молча
        if ticker not in data_dict or data_dict[ticker].empty:
            logging.warning(f"ALERTS_LEVEL: по тикеру {ticker} нет данных — пропущен")
            continue

        df = data_dict[ticker]
        close = df['close']
        prev = close.shift(1)
        window_start = df['begin'].iloc[-1] - pd.Timedelta(days=alerts_days)
        for level in levels:
            # Пересечение: close перешёл уровень (достижение уровня — тоже сигнал)
            crossed = ((prev < level) & (close >= level)) | ((prev > level) & (close <= level))
            hits = df[crossed]
            crossed_at = hits['begin'].iloc[-1] if not hits.empty else None
            signals.append({'ticker': ticker,
                            'name': assets_config[ticker]['name'],
                            'crossed_at': crossed_at,
                            'level': level,
                            'price': close.iloc[-1],
                            'actual': crossed_at is not None and crossed_at >= window_start})
    return signals
