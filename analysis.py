"""Расчёт уровней «Трёх цен» и цветовых меток — чистые функции без I/O."""

import pandas as pd


def compute_levels(df: pd.DataFrame) -> tuple[float, float, float, float]:
    """Уровни по отфильтрованным данным: (min, ⅓ диапазона, ⅔ диапазона, max).

    Единственная формула уровней в проекте — и для меток, и для линий графиков.
    """
    min_p = df['close'].min()
    max_p = df['close'].max()
    range_ = max_p - min_p
    return min_p, min_p + range_ * (1 / 3), min_p + range_ * (2 / 3), max_p


def classify_price(current_price: float, levels: tuple[float, float, float, float]) -> tuple[str, str]:
    """Классификация текущей цены по диапазону: возвращает (метка, цвет текста)."""
    _, level_1_3, level_2_3, _ = levels
    if current_price <= level_1_3:
        return 'низкая', 'green'
    if current_price <= level_2_3:
        return 'средняя', 'black'
    return 'высокая', 'red'


def build_price_maps(data_dict: dict[str, pd.DataFrame]) -> tuple[dict[str, str], dict[str, str]]:
    """Для каждого тикера — метка диапазона и цвет текста в таблице."""
    price_level_map: dict[str, str] = {}
    price_color_map: dict[str, str] = {}

    for ticker, df in data_dict.items():
        if df.empty or df['close'].isna().all():
            price_level_map[ticker] = '—'
            price_color_map[ticker] = 'gray'
            continue

        levels = compute_levels(df)
        current_price = df['close'].iloc[-1]
        label, color = classify_price(current_price, levels)

        price_level_map[ticker] = label
        price_color_map[ticker] = color

    return price_level_map, price_color_map
