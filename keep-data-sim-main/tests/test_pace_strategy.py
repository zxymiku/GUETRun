from unittest import TestCase

from keep_data_sim.config.schema import PaceConfig
from keep_data_sim.metrics.pace_strategy import create_pace_strategy


class PaceStrategyTests(TestCase):
    def test_negative_split_is_faster_in_second_half(self) -> None:
        strategy = create_pace_strategy(
            PaceConfig(
                strategy="negative_split",
                avg_pace_min_per_km=5.0,
                negative_split_ratio=0.95,
                warmup_duration_s=0.0,
            ),
            sport="running",
        )

        first_half_speed = strategy.speed_at(1000, 5000, 600)
        second_half_speed = strategy.speed_at(4000, 5000, 1800)

        self.assertGreater(second_half_speed, first_half_speed)

    def test_positive_split_is_faster_in_first_half(self) -> None:
        strategy = create_pace_strategy(
            PaceConfig(
                strategy="positive_split",
                avg_pace_min_per_km=5.0,
                positive_split_ratio=1.05,
                warmup_duration_s=0.0,
            ),
            sport="running",
        )

        first_half_speed = strategy.speed_at(1000, 5000, 600)
        second_half_speed = strategy.speed_at(4000, 5000, 1800)

        self.assertGreater(first_half_speed, second_half_speed)
