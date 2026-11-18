"""Core technical indicators for QUANT PILOT."""

from __future__ import annotations

import numpy as np


def sma(values: list[float], period: int) -> list[float]:
    """Simple moving average."""
    if len(values) < period:
        return [float("nan")] * len(values)
    out = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(float("nan"))
        else:
            out.append(float(np.mean(values[i - period + 1 : i + 1])))
    return out


def ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average."""
    if len(values) < period:
        return [float("nan")] * len(values)
    alpha = 2.0 / (period + 1)
    out = [float(values[0])]
    for i in range(1, len(values)):
        out.append(float(values[i] * alpha + out[-1] * (1 - alpha)))
    return out


def rsi(values: list[float], period: int = 14) -> list[float]:
    """Relative Strength Index."""
    if len(values) < period + 1:
        return [float("nan")] * len(values)
    out = [float("nan")] * len(values)
    gains = []
    losses = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = float(np.mean(gains[:period])) if len(gains) >= period else 0.0
    avg_loss = float(np.mean(losses[:period])) if len(losses) >= period else 0.0
    for i in range(period, len(values)):
        if i == period:
            avg_gain = float(np.mean(gains[:period]))
            avg_loss = float(np.mean(losses[:period]))
        else:
            delta = values[i] - values[i - 1]
            gain = max(delta, 0.0)
            loss = max(-delta, 0.0)
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float]:
    """Average True Range."""
    n = len(highs)
    if n < 2:
        return [float("nan")] * n
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    out = [float("nan")] * n
    if n >= period:
        out[period - 1] = float(np.mean(trs[:period]))
        for i in range(period, n):
            out[i] = (out[i - 1] * (period - 1) + trs[i]) / period
    return out


def swing_highs(highs: list[float], lookback: int = 2) -> list[float]:
    """Simple swing highs using fractal method."""
    out = []
    for i in range(lookback, len(highs) - lookback):
        window = highs[i - lookback : i + lookback + 1]
        if highs[i] == max(window):
            out.append(highs[i])
    return out


def swing_lows(lows: list[float], lookback: int = 2) -> list[float]:
    """Simple swing lows using fractal method."""
    out = []
    for i in range(lookback, len(lows) - lookback):
        window = lows[i - lookback : i + lookback + 1]
        if lows[i] == min(window):
            out.append(lows[i])
    return out


def equal_highs(highs: list[float], tolerance: float = 0.5) -> list[list[float]]:
    """Detect equal highs (liquidity pools above price)."""
    groups: dict[float, list[float]] = {}
    for h in highs:
        key = round(h / tolerance) * tolerance
        groups.setdefault(key, []).append(h)
    return [v for v in groups.values() if len(v) >= 2]


def equal_lows(lows: list[float], tolerance: float = 0.5) -> list[list[float]]:
    """Detect equal lows (liquidity pools below price)."""
    groups: dict[float, list[float]] = {}
    for l in lows:
        key = round(l / tolerance) * tolerance
        groups.setdefault(key, []).append(l)
    return [v for v in groups.values() if len(v) >= 2]


def bollinger_bands(values: list[float], period: int = 20, std_dev: float = 2.0):
    """Bollinger Bands."""
    n = len(values)
    middle = sma(values, period)
    upper = [float("nan")] * n
    lower = [float("nan")] * n
    for i in range(period - 1, n):
        window = np.array(values[i - period + 1 : i + 1])
        std = float(np.std(window, ddof=0))
        upper[i] = middle[i] + std_dev * std
        lower[i] = middle[i] - std_dev * std
    return middle, upper, lower