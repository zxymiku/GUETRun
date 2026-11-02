"""Data smoothing utilities."""

from __future__ import annotations

import numpy as np


def moving_average(data: np.ndarray, window: int = 5) -> np.ndarray:
    """Apply centered moving average smoothing."""
    if len(data) < window:
        return data.copy()
    kernel = np.ones(window) / window
    padded = np.pad(data, window // 2, mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")
    return smoothed[: len(data)]


def exponential_smoothing(data: np.ndarray, alpha: float = 0.3) -> np.ndarray:
    """Apply exponential smoothing."""
    result = np.empty_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result
