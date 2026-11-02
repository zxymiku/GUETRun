"""Pace strategy implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from keep_data_sim.config.schema import PaceConfig


class PaceStrategy(ABC):
    """Compute instantaneous speed at a given point in the workout."""

    @abstractmethod
    def speed_at(self, distance_m: float, total_distance_m: float, elapsed_s: float) -> float:
        """Return instantaneous speed in m/s at given cumulative distance."""
        ...


class ConstantPace(PaceStrategy):
    """Maintain constant speed throughout."""

    def __init__(self, config: PaceConfig, sport: str) -> None:
        if sport == "running":
            self._target_speed = 1000.0 / (config.avg_pace_min_per_km * 60.0)
        else:
            self._target_speed = config.avg_speed_kmh / 3.6
        self._warmup_duration_s = config.warmup_duration_s
        self._warmup_factor = config.warmup_speed_factor

    def speed_at(self, distance_m: float, total_distance_m: float, elapsed_s: float) -> float:
        if elapsed_s < self._warmup_duration_s:
            return self._target_speed * self._warmup_factor
        return self._target_speed


class NegativeSplitPace(PaceStrategy):
    """Faster in the second half of the workout."""

    def __init__(self, config: PaceConfig, sport: str) -> None:
        if sport == "running":
            self._avg_speed = 1000.0 / (config.avg_pace_min_per_km * 60.0)
        else:
            self._avg_speed = config.avg_speed_kmh / 3.6
        self._ratio = config.negative_split_ratio
        # A ratio below 1.0 means the second half pace is lower/faster.
        # Since this class works in speed, second_half_speed = first / ratio.
        self._first_half_speed = self._avg_speed * 2 / (1 + 1 / self._ratio)
        self._second_half_speed = self._first_half_speed / self._ratio
        self._warmup_duration_s = config.warmup_duration_s
        self._warmup_factor = config.warmup_speed_factor

    def speed_at(self, distance_m: float, total_distance_m: float, elapsed_s: float) -> float:
        warmup_factor = self._warmup_factor if elapsed_s < self._warmup_duration_s else 1.0
        if distance_m < total_distance_m / 2:
            return self._first_half_speed * warmup_factor
        return self._second_half_speed * warmup_factor


class PositiveSplitPace(PaceStrategy):
    """Faster in the first half of the workout."""

    def __init__(self, config: PaceConfig, sport: str) -> None:
        if sport == "running":
            self._avg_speed = 1000.0 / (config.avg_pace_min_per_km * 60.0)
        else:
            self._avg_speed = config.avg_speed_kmh / 3.6
        self._ratio = config.positive_split_ratio
        self._first_half_speed = self._avg_speed * 2 / (1 + 1 / self._ratio)
        self._second_half_speed = self._first_half_speed / self._ratio
        self._warmup_duration_s = config.warmup_duration_s
        self._warmup_factor = config.warmup_speed_factor

    def speed_at(self, distance_m: float, total_distance_m: float, elapsed_s: float) -> float:
        warmup_factor = self._warmup_factor if elapsed_s < self._warmup_duration_s else 1.0
        if distance_m < total_distance_m / 2:
            return self._first_half_speed * warmup_factor
        return self._second_half_speed * warmup_factor


class IntervalPace(PaceStrategy):
    """Alternating fast and slow segments."""

    def __init__(self, config: PaceConfig, sport: str) -> None:
        if sport == "running":
            self._fast_speed = 1000.0 / (config.interval_fast_min_per_km * 60.0)
            self._slow_speed = 1000.0 / (config.interval_slow_min_per_km * 60.0)
        else:
            self._fast_speed = config.interval_fast_speed_kmh / 3.6
            self._slow_speed = config.interval_slow_speed_kmh / 3.6
        self._fast_duration_s = config.interval_fast_duration_s
        self._slow_duration_s = config.interval_slow_duration_s
        self._cycle_duration_s = self._fast_duration_s + self._slow_duration_s
        self._warmup_duration_s = config.warmup_duration_s
        self._warmup_factor = config.warmup_speed_factor

    def speed_at(self, distance_m: float, total_distance_m: float, elapsed_s: float) -> float:
        if elapsed_s < self._warmup_duration_s:
            return self._slow_speed * self._warmup_factor

        effective_elapsed = elapsed_s - self._warmup_duration_s
        position_in_cycle = effective_elapsed % self._cycle_duration_s

        if position_in_cycle < self._fast_duration_s:
            return self._fast_speed
        return self._slow_speed


# Registry
_PACE_STRATEGIES: dict[str, type[PaceStrategy]] = {
    "constant": ConstantPace,
    "negative_split": NegativeSplitPace,
    "positive_split": PositiveSplitPace,
    "interval": IntervalPace,
}


def create_pace_strategy(config: PaceConfig, sport: str) -> PaceStrategy:
    """Factory function to create a pace strategy from config."""
    cls = _PACE_STRATEGIES.get(config.strategy)
    if cls is None:
        raise ValueError(f"Unknown pace strategy: {config.strategy}")
    return cls(config, sport)
