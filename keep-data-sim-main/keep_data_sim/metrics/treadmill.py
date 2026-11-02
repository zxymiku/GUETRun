"""Realistic, temporally correlated treadmill metric curves."""

from __future__ import annotations

import numpy as np

from keep_data_sim.config.schema import CadenceConfig, HeartRateConfig


def generate_treadmill_speed_curve(
    base_speeds: np.ndarray,
    elapsed_times: np.ndarray,
    target_distance_m: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Add smooth wrist-sensor-like speed variation and preserve total distance."""
    if len(base_speeds) == 0:
        return np.array([], dtype=float)

    variation = _smooth_control_curve(
        len(base_speeds),
        anchor_interval=30,
        rho=0.65,
        smoothing_window=9,
        rng=rng,
    )
    speeds = base_speeds * (1.0 + 0.035 * variation)
    speeds = np.maximum(speeds, 0.5)

    integrated_distance = float(np.trapezoid(speeds, elapsed_times))
    if integrated_distance <= 0:
        raise ValueError("Treadmill speed curve must cover a positive distance")
    return speeds * (target_distance_m / integrated_distance)


def integrate_treadmill_distance(
    speeds: np.ndarray,
    elapsed_times: np.ndarray,
    target_distance_m: float,
) -> np.ndarray:
    """Integrate point speeds with the trapezoid rule and pin the final distance."""
    if len(speeds) != len(elapsed_times):
        raise ValueError("Speed and timestamp arrays must have the same length")
    if len(speeds) == 0:
        return np.array([], dtype=float)

    intervals = np.diff(elapsed_times)
    increments = (speeds[:-1] + speeds[1:]) * 0.5 * intervals
    distances = np.concatenate(([0.0], np.cumsum(increments)))
    if distances[-1] <= 0:
        raise ValueError("Treadmill distance must be positive")
    distances *= target_distance_m / distances[-1]
    distances[-1] = target_distance_m
    return distances


def generate_treadmill_heart_rate_curve(
    elapsed_times: np.ndarray,
    config: HeartRateConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate warm-up rise, cardiac drift, and smooth sensor variation."""
    if len(elapsed_times) == 0:
        return np.array([], dtype=int)

    duration = max(float(elapsed_times[-1]), 1.0)
    warmup = -30.0 * np.exp(-elapsed_times / 120.0)
    cardiac_drift = 6.0 * elapsed_times / duration
    noise_scale = min(max(config.noise_std * 0.25, 0.5), 1.2)
    sensor_variation = (
        _smooth_control_curve(
            len(elapsed_times),
            anchor_interval=20,
            rho=0.70,
            smoothing_window=7,
            rng=rng,
        )
        * noise_scale
    )

    values = config.avg_hr + warmup + cardiac_drift + sensor_variation
    values += config.avg_hr - float(np.mean(values))
    return _round_to_target_mean(
        values,
        target=config.avg_hr,
        lower=config.resting_hr,
        upper=config.max_hr,
    )


def generate_treadmill_cadence_curve(
    speeds: np.ndarray,
    config: CadenceConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate smooth cadence coupled weakly to the measured speed curve."""
    if len(speeds) == 0:
        return np.array([], dtype=int)

    speed_std = float(np.std(speeds))
    if speed_std > 0:
        normalized_speed = (speeds - float(np.mean(speeds))) / speed_std
    else:
        normalized_speed = np.zeros_like(speeds)

    cadence_noise = _smooth_control_curve(
        len(speeds),
        anchor_interval=20,
        rho=0.70,
        smoothing_window=7,
        rng=rng,
    )
    noise_scale = max(1.5, config.running_range_spm * 0.22)
    values = (
        config.running_avg_spm
        + 0.75 * normalized_speed
        + noise_scale * cadence_noise
    )
    values += config.running_avg_spm - float(np.mean(values))
    return _round_to_target_mean(
        values,
        target=config.running_avg_spm,
        lower=140,
        upper=200,
    )


def _smooth_control_curve(
    size: int,
    anchor_interval: int,
    rho: float,
    smoothing_window: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Interpolate correlated controls and soften corners without point noise."""
    if size <= 1:
        return np.zeros(size, dtype=float)

    anchor_positions = np.arange(0, size, anchor_interval, dtype=int)
    if anchor_positions[-1] != size - 1:
        anchor_positions = np.append(anchor_positions, size - 1)
    anchor_values = _standardized_ar1(len(anchor_positions), rho, rng)
    values = np.interp(np.arange(size), anchor_positions, anchor_values)

    window_size = max(3, smoothing_window | 1)
    window = np.hanning(window_size)
    window /= float(np.sum(window))
    padding = window_size // 2
    padded = np.pad(values, (padding, padding), mode="edge")
    values = np.convolve(padded, window, mode="valid")

    values -= float(np.mean(values))
    standard_deviation = float(np.std(values))
    if standard_deviation > 0:
        values /= standard_deviation
    return values


def _standardized_ar1(
    size: int,
    rho: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return a zero-mean, unit-variance stationary AR(1) sequence."""
    if size <= 1:
        return np.zeros(size, dtype=float)

    values = np.empty(size, dtype=float)
    values[0] = rng.normal()
    innovation_scale = np.sqrt(1.0 - rho * rho)
    for index in range(1, size):
        values[index] = (
            rho * values[index - 1]
            + innovation_scale * rng.normal()
        )

    values -= float(np.mean(values))
    standard_deviation = float(np.std(values))
    if standard_deviation > 0:
        values /= standard_deviation
    return values


def _round_to_target_mean(
    values: np.ndarray,
    target: int,
    lower: int,
    upper: int,
) -> np.ndarray:
    """Round and bound an already mean-centered smooth curve."""
    del target  # Centering happens before rounding; FIT summaries round the mean.
    return np.rint(np.clip(values, lower, upper)).astype(int)
