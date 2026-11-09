""""Three Prices" level computation and color labels — pure functions without I/O."""

import pandas as pd


def compute_levels(df: pd.DataFrame) -> tuple[float, float, float, float]:
    """Levels over the filtered data: (min, 1/3 of the range, 2/3 of the range, max).

    The only levels formula in the project: it is used both by the range
    labels and by the dashed chart lines (the formula used to be duplicated).
    """
    min_p = df['close'].min()
    max_p = df['close'].max()
    range_ = max_p - min_p
    return min_p, min_p + range_ * (1 / 3), min_p + range_ * (2 / 3), max_p


def classify_price(current_price: float, levels: tuple[float, float, float, float]) -> tuple[str, str]:
    """Classify the current price into a range: returns (label, text color)."""
    _, level_1_3, level_2_3, _ = levels
    if current_price <= level_1_3:
        return 'низкая', 'green'
    if current_price <= level_2_3:
        return 'средняя', 'black'
    return 'высокая', 'red'


def build_price_maps(data_dict: dict[str, pd.DataFrame]) -> tuple[dict[str, str], dict[str, str]]:
    """For each ticker, return the range label and the table text color."""
    price_level_map: dict[str, str] = {}
    price_color_map: dict[str, str] = {}

    for ticker, df in data_dict.items():
        if df.empty or df['close'].isna().all():
            price_level_map[ticker] = '—'
            price_color_map[ticker] = 'gray'
            continue

        # Levels are computed strictly over the filtered data
        levels = compute_levels(df)
        current_price = df['close'].iloc[-1]
        label, color = classify_price(current_price, levels)

        price_level_map[ticker] = label
        price_color_map[ticker] = color

    return price_level_map, price_color_map
