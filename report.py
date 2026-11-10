"""Формирование PDF-отчёта «Трёх цен»: титул с таблицей, доходность, распределение и графики по тикерам."""

import logging

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.table import Table

import config
from analysis import compute_levels


def _return_color(v: float, vmax: float, vmin: float):
    """(rgb, насыщенность) для доходности v: прибыль — зелёный, убыток — красный;
    насыщенность растёт с удалением от нуля (нижний порог SAT_MIN)."""
    if v >= 0:
        s = config.SAT_MIN + (1.0 - config.SAT_MIN) * (v / vmax) if vmax > 0 else config.SAT_MIN
        base = config.GREEN_BASE
    else:
        s = config.SAT_MIN + (1.0 - config.SAT_MIN) * (v / vmin) if vmin < 0 else config.SAT_MIN
        base = config.RED_BASE
    return tuple(1.0 - s + s * c for c in base), s


def plural_years(n: int) -> str:
    """Склонение русского слова «год»: 1 год / 2–4 года / 5–20 лет (11–14 учтены)."""
    if n % 10 == 1 and n % 100 != 11:
        return "год"
    if n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]:
        return "года"
    return "лет"


def assign_chart_colors(data_dict: dict, assets_config: dict) -> dict[str, str]:
    """Цвета линий назначаются в порядке исходного словаря конфига."""
    ordered_tickers = [ticker for ticker in assets_config if ticker in data_dict]
    return {ticker: config.BASE_COLORS[i % len(config.BASE_COLORS)] for i, ticker in enumerate(ordered_tickers)}


def _build_table_rows(data_dict: dict, assets_config: dict,
                      price_level_map: dict, price_color_map: dict) -> list:
    """Строки титульной таблицы: шапка + по строке на тикер в порядке ASSETS_CONFIG_RF."""
    table_data = [['№', 'Тикер', 'Наименование', 'Текущая цена', 'Диапазон цены']]

    row_number = 0
    for ticker, cfg in assets_config.items():
        if ticker in data_dict and not data_dict[ticker].empty:
            row_number += 1
            last_price = data_dict[ticker]['close'].iloc[-1]
            price_str = f'{last_price:.2f}'
            level = price_level_map[ticker]
            table_data.append([str(row_number), ticker, cfg['name'], price_str, level,
                               price_color_map[ticker]])
    return table_data


def _build_title_figure(table_data: list, params, continuation: bool = False):
    """Фигура титула: шапка (кроме страниц продолжения) и таблица (часть строк)."""
    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_subplot(111)
    ax.axis('off')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Шапка с датой — только на первой странице титула
    if not continuation:
        ax.text(0.5, 0.97, f'{params.today_str}. Три ценовых диапазона',
                fontsize=20, fontweight='bold', ha='center', transform=ax.transAxes)
        subtitle = (f'Анализ за {params.years} {plural_years(params.years)} '
                    f'(с {params.start_date.strftime("%d.%m.%Y")})')
        ax.text(0.5, 0.91, subtitle,
                fontsize=14, ha='center', transform=ax.transAxes)

    col_widths = [0.05, 0.10, 0.34, 0.17, 0.19]
    row_height = 0.052
    n_rows = len(table_data)
    table_height = n_rows * row_height
    table_bottom = 0.88 - table_height

    table = Table(ax, bbox=[0.07, table_bottom, 0.86, table_height])

    n_cols = len(table_data[0])
    for i, row in enumerate(table_data):
        for j in range(n_cols):
            cell = row[j]
            facecolor = '#e0e0e0' if i == 0 else '#ffffff'
            fontweight = 'bold' if i == 0 else 'normal'

            cell_loc = 'center'
            text_to_display = cell

            if j == 0 or j == 1:
                cell_loc = 'center'
                text_to_display = cell
            elif j == 2:
                cell_loc = 'left'
                text_to_display = f" {cell}"
            elif j == 3:
                cell_loc = 'right'
                text_to_display = f"{cell}  "

            cell_obj = table.add_cell(i, j, width=col_widths[j], height=row_height,
                                      text=text_to_display, loc=cell_loc, facecolor=facecolor)
            cell_obj.get_text().set_fontweight(fontweight)
            cell_obj.get_text().set_fontsize(10)

            # Цвет колонки «Диапазон цены» (j=4) лежит в row[5]
            if i > 0 and j == 4:
                cell_obj.get_text().set_color(row[5])

    table.auto_set_font_size(False)  # иначе matplotlib сжимает каждую ячейку под самый длинный текст
    ax.add_table(table)

    # Поля страницы
    plt.subplots_adjust(left=0.1, right=0.9, top=0.97, bottom=0.2)
    return fig


def _render_title_pages(pdf: PdfPages, data_dict: dict, assets_config: dict,
                        price_level_map: dict, price_color_map: dict, params) -> None:
    """Титульные страницы: при большом числе тикеров таблица продолжается
    на следующих страницах (по ROWS_PER_PAGE строк, шапка повторяется)."""
    table_data = _build_table_rows(data_dict, assets_config, price_level_map, price_color_map)
    header, rows = table_data[0], table_data[1:]
    for start in range(0, len(rows), config.ROWS_PER_PAGE):
        fig = _build_title_figure([header] + rows[start:start + config.ROWS_PER_PAGE], params,
                                  continuation=start > 0)
        pdf.savefig(fig, dpi=150, metadata={'Creator': 'Python'})
        plt.close(fig)


def _compute_returns(data_dict: dict) -> dict[str, float]:
    """Доходность тикера за период: (последняя close / первая − 1) · 100 %.
    data_dict уже отфильтрован по start_date, поэтому «первая» — первый
    торговый день периода."""
    returns: dict[str, float] = {}
    for ticker, df in data_dict.items():
        if df.empty:
            continue
        first_price = df['close'].iloc[0]
        last_price = df['close'].iloc[-1]
        if first_price:
            returns[ticker] = (last_price / first_price - 1.0) * 100.0
    return returns


def _build_returns_figure(data_dict: dict, params):
    """Фигура «доходность по тикерам»: горизонтальные полосы по убыванию.
    Полосы направлены вправо: длина — модуль доходности, знак — в подписи и в
    цвете (прибыль зелёным, убыток красным; насыщенность растёт от нуля)."""
    returns = _compute_returns(data_dict)
    sorted_tickers = sorted(returns, key=lambda t: returns[t], reverse=True)
    values = [returns[t] for t in sorted_tickers]

    fig, ax = plt.subplots(figsize=(14, 8))

    vmax, vmin = max(values), min(values)
    colors = [_return_color(v, vmax, vmin)[0] for v in values]

    lengths = [abs(v) for v in values]
    max_abs = max(lengths) if lengths else 1.0

    y_pos = list(range(len(sorted_tickers)))
    bars = ax.barh(y_pos, lengths, color=colors, height=0.72)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_tickers, fontsize=10)
    ax.invert_yaxis()  # лучшая доходность сверху, как в образце

    ax.bar_label(bars, labels=[f'{v:+.1f}%' for v in values], padding=4, fontsize=9)

    # Ноль вплотную к оси тикеров; справа запас под подписи
    pad = max_abs * 0.08 + 1.0
    ax.set_xlim(0, max_abs + pad)

    ax.grid(axis='x', alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_xlabel('Доходность, %', fontsize=12)

    fig.suptitle('Доходность по тикерам', fontsize=20, fontweight='bold', y=0.97)
    fig.text(0.5, 0.905,
             f'Период: с {params.start_date.strftime("%d.%m.%Y")} по {params.today_str}',
             ha='center', fontsize=13, color='#555555')

    fig.tight_layout(rect=[0, 0, 1, 0.86])
    return fig


def _render_returns_page(pdf: PdfPages, data_dict: dict, params) -> None:
    """Страница 2 отчёта: график доходности всех тикеров за период."""
    if not _compute_returns(data_dict):
        logging.warning("Нет данных для расчёта доходности — страница пропущена")
        return
    fig = _build_returns_figure(data_dict, params)
    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def plural_tickers(n: int) -> str:
    """Склонение русского слова «тикер»: 1 тикер / 2–4 тикера / 5–20 тикеров."""
    if n % 10 == 1 and n % 100 != 11:
        return 'тикер'
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 'тикера'
    return 'тикеров'


BUCKETS = [
    ('< −80%', None, -80),
    ('−80…−60%', -80, -60),
    ('−60…−40%', -60, -40),
    ('−40…−20%', -40, -20),
    ('−20…0%', -20, 0),
    ('0…+20%', 0, 20),
    ('+20…+40%', 20, 40),
    ('+40…+60%', 40, 60),
    ('+60…+80%', 60, 80),
    ('≥ +80%', 80, None),
]


def _build_distribution_figure(data_dict: dict, params):
    """Фигура «распределение тикеров по доходности» в стиле образца: колонки
    диапазонов по 20 %, в каждой — подписанные ячейки тикеров; цвет ячейки
    совпадает с графиком доходности (зелёный/красный, насыщенность от нуля)."""
    returns = _compute_returns(data_dict)
    vmax, vmin = max(returns.values()), min(returns.values())

    columns = []
    for label, lo, hi in BUCKETS:
        items = [(t, v) for t, v in returns.items()
                 if (lo is None or v >= lo) and (hi is None or v < hi)]
        items.sort(key=lambda x: x[1])  # самые крайние значения внизу колонки
        columns.append((label, items))

    n_cols = len(BUCKETS)
    max_height = max((len(items) for _, items in columns), default=0)

    fig, ax = plt.subplots(figsize=(14, 8))

    cell_w = 0.86
    for i, (label, items) in enumerate(columns):
        for k, (ticker, v) in enumerate(items):
            color, s = _return_color(v, vmax, vmin)
            ax.add_patch(plt.Rectangle((i - cell_w / 2, k), cell_w, 1.0,
                                       facecolor=color, edgecolor='white', linewidth=1.5))
            text_color = 'white' if s >= 0.7 else '#222222'
            ax.text(i, k + 0.5, f'{ticker} {v:+.1f}%',
                    ha='center', va='center', fontsize=9, color=text_color)
        if items:
            ax.text(i, len(items) + 0.3, f'{len(items)} {plural_tickers(len(items))}',
                    ha='center', va='bottom', fontsize=10, color='#555555')

    ax.set_xlim(-0.55, n_cols - 0.45)
    ax.set_ylim(-0.2, max_height + 1.7)
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels([label for label, _, _ in BUCKETS], fontsize=10)
    ax.tick_params(axis='x', length=0)
    ax.set_yticks([])
    for spine in ('top', 'right', 'left'):
        ax.spines[spine].set_visible(False)

    fig.suptitle('Распределение тикеров по доходности', fontsize=20, fontweight='bold', y=0.97)
    fig.text(0.5, 0.905,
             f'Период: с {params.start_date.strftime("%d.%m.%Y")} по {params.today_str}',
             ha='center', fontsize=13, color='#555555')

    fig.tight_layout(rect=[0, 0, 1, 0.86])
    return fig


def _render_distribution_page(pdf: PdfPages, data_dict: dict, params) -> None:
    """Страница 3 отчёта: распределение тикеров по диапазонам доходности."""
    if not _compute_returns(data_dict):
        logging.warning("Нет данных для распределения доходности — страница пропускается")
        return
    fig = _build_distribution_figure(data_dict, params)
    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def _render_ticker_chart(pdf: PdfPages, ticker: str, df: pd.DataFrame, cfg: dict, color: str, params) -> None:
    """Страница с графиком одного тикера и пунктирными уровнями «трёх цен»."""
    min_p, level_1_3, level_2_3, max_p = (round(v, 2) for v in compute_levels(df))
    key_levels = sorted({min_p, level_1_3, level_2_3, max_p})
    key_levels_str = [f'{lvl:.2f}' for lvl in key_levels]

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(df['begin'], df['close'], color=color, linewidth=1.0)

    for level in key_levels:
        ax.axhline(y=level, color=config.LEVEL_COLOR, linestyle='--', linewidth=1.2)

    y_ticks = sorted(set(list(ax.get_yticks()) + key_levels))
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f'{y:.2f}' for y in y_ticks])

    for label in ax.yaxis.get_ticklabels():
        if label.get_text() in key_levels_str:
            label.set_color(config.LEVEL_COLOR)

    asset_name = cfg['name']
    currency = cfg['currency']

    ax.set_title(f'{asset_name} ({ticker}) — за {params.years} {plural_years(params.years)}',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel(f'Цена ({currency})', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', rotation=0)
    ax.set_xlabel('')
    plt.tight_layout()
    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def generate_pdf(pdf_path: str, data_dict: dict, assets_config: dict,
                 price_level_map: dict, price_color_map: dict, params) -> None:
    """Сборка PDF: титульные страницы с таблицей тикеров, затем страницы
    доходности и распределения, затем по графику на тикер в порядке конфига."""
    close_colors = assign_chart_colors(data_dict, assets_config)

    with PdfPages(pdf_path) as pdf:
        # --- Титульные страницы: таблица тикеров ---
        _render_title_pages(pdf, data_dict, assets_config, price_level_map, price_color_map, params)

        # --- Страница 2: доходность по тикерам за период ---
        _render_returns_page(pdf, data_dict, params)

        # --- Страница 3: распределение тикеров по доходности ---
        _render_distribution_page(pdf, data_dict, params)

        # --- Графики: строго в порядке ASSETS_CONFIG_RF ---
        for ticker in assets_config:
            if ticker not in data_dict:
                continue
            _render_ticker_chart(pdf, ticker, data_dict[ticker], assets_config[ticker],
                                 close_colors[ticker], params)
