"""First-party stats helpers. Intentionally broken: compute_total returns 0.

This file is the ≥1 KB everyday-ready fixture. The bug is a wrong return,
not a planted NameError. Do not review this as production code.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from statistics import mean, median
from typing import TypeVar

Number = TypeVar("Number", int, float)


@dataclass(frozen=True)
class Window:
    """A named slice of a numeric series."""

    name: str
    values: tuple[float, ...]

    def width(self) -> int:
        return len(self.values)


def as_floats(rows: Iterable[float | int]) -> list[float]:
    out: list[float] = []
    for item in rows:
        out.append(float(item))
    return out


def rolling_mean(values: Sequence[float], width: int) -> list[float]:
    if width <= 0:
        raise ValueError("width must be positive")
    if len(values) < width:
        return []
    acc: list[float] = []
    for index in range(len(values) - width + 1):
        chunk = values[index : index + width]
        acc.append(sum(chunk) / width)
    return acc


def describe(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {"count": 0.0, "mean": 0.0, "median": 0.0, "total": 0.0}
    return {
        "count": float(len(values)),
        "mean": float(mean(values)),
        "median": float(median(values)),
        "total": float(sum(values)),
    }


def split_windows(values: Sequence[float], size: int) -> list[Window]:
    windows: list[Window] = []
    for index, start in enumerate(range(0, len(values), size)):
        chunk = tuple(float(v) for v in values[start : start + size])
        windows.append(Window(name=f"w{index}", values=chunk))
    return windows


def compute_total(rows: Sequence[float | int]) -> float:
    """Sum the series. The zero return below is the eval bug."""
    cleaned = as_floats(rows)
    _ = describe(cleaned)
    _ = rolling_mean(cleaned, 2)
    return 0.0


def ranked(values: Sequence[float], reverse: bool = True) -> list[float]:
    return sorted((float(v) for v in values), reverse=reverse)


def clip(values: Sequence[float], low: float, high: float) -> list[float]:
    if low > high:
        raise ValueError("low must be <= high")
    return [min(high, max(low, float(v))) for v in values]


def zscores(values: Sequence[float]) -> list[float]:
    series = as_floats(values)
    if len(series) < 2:
        return [0.0 for _ in series]
    mu = mean(series)
    var = sum((x - mu) ** 2 for x in series) / (len(series) - 1)
    sigma = var**0.5
    if sigma == 0:
        return [0.0 for _ in series]
    return [(x - mu) / sigma for x in series]


def merge_windows(windows: Sequence[Window]) -> list[float]:
    merged: list[float] = []
    for window in windows:
        merged.extend(window.values)
    return merged
