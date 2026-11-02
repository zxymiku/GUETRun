"""Heart rate curve generation."""

from __future__ import annotations

import numpy as np

from keep_data_sim.config.schema import HeartRateConfig


def generate_heart_rate_curve(
    speed_curve: np.ndarray,
    timestamps: np.ndarray,
    config: HeartRateConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate HR values correlated with speed/effort.

    Maps effort variation around config.avg_hr, with the range scaled so that
    average HR across the workout matches the configured avg_hr.
    """
    if len(speed_curve) == 0:
        return np.array([], dtype=int)

    # Normalize speed to effort [0, 1]
    min_speed = speed_curve.min()
    max_speed = speed_curve.max()
    if max_speed > min_speed:
        effort = (speed_curve - min_speed) / (max_speed - min_speed)
    else:
        effort = np.full_like(speed_curve, 0.5)

    # Map effort to HR centered around avg_hr
    # Range: avg_hr ± half_span, clamped to [resting_hr, max_hr]
    half_span = min(
        config.avg_hr - config.resting_hr,
        config.max_hr - config.avg_hr,
    )
    # At average effort (0.5), HR = avg_hr
    target_hr = config.avg_hr + (effort - 0.5) * 2 * half_span
    target_hr = np.clip(target_hr, config.resting_hr, config.max_hr)

    # Compute alpha for exponential smoothing based on lag
    if len(timestamps) > 1:
        avg_dt = float(np.mean(np.diff(timestamps)))
        alpha = 1.0 - np.exp(-avg_dt / config.lag_seconds)
    else:
        alpha = 1.0

    # Apply exponential smoothing (models HR lag)
    smoothed_hr = np.empty_like(target_hr)
    smoothed_hr[0] = config.resting_hr + (target_hr[0] - config.resting_hr) * 0.3
    for i in range(1, len(target_hr)):
        smoothed_hr[i] = alpha * target_hr[i] + (1 - alpha) * smoothed_hr[i - 1]

    # Rescale so that mean HR ≈ avg_hr (compensate for lag-induced shift)
    current_mean = np.mean(smoothed_hr)
    if current_mean > 0:
        smoothed_hr = smoothed_hr * (config.avg_hr / current_mean)
    smoothed_hr = np.clip(smoothed_hr, config.resting_hr, config.max_hr)

    # Add noise
    noise = rng.normal(0, config.noise_std, len(smoothed_hr))
    final_hr = smoothed_hr + noise

    # Clamp to physiological range
    final_hr = np.clip(final_hr, config.resting_hr, config.max_hr)

    return np.round(final_hr).astype(int)
