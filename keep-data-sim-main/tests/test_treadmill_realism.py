from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np
from garmin_fit_sdk import Decoder, Stream

from keep_data_sim.config.schema import (
    CadenceConfig,
    HeartRateConfig,
    PaceConfig,
    SimConfig,
)
from keep_data_sim.core.simulator import Simulator
from keep_data_sim.export.fit_exporter import FitExporter


def lag_one_correlation(values: np.ndarray) -> float:
    return float(np.corrcoef(values[:-1], values[1:])[0, 1])


def direction_reversal_ratio(values: np.ndarray) -> float:
    differences = np.diff(values)
    return float(np.mean(differences[:-1] * differences[1:] < 0))


class TreadmillRealismTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = SimConfig(
            treadmill=True,
            distance_m=10000.0,
            start_time=datetime(2026, 7, 30, 2, 0, tzinfo=timezone.utc),
            pace=PaceConfig(
                strategy="constant",
                avg_pace_min_per_km=5.9,
                warmup_duration_s=0.0,
            ),
            heart_rate=HeartRateConfig(avg_hr=152, noise_std=3.0),
            cadence=CadenceConfig(running_avg_spm=172),
            output_formats=("fit",),
            seed=20260730,
        )
        cls.points = Simulator(cls.config).simulate()

    def test_speed_is_smoothly_variable_and_preserves_targets(self) -> None:
        speeds = np.asarray([point.speed for point in self.points])
        duration = (
            self.points[-1].timestamp - self.points[0].timestamp
        ).total_seconds()

        self.assertEqual(len(self.points), 3541)
        self.assertEqual(self.points[-1].distance, 10000.0)
        self.assertEqual(duration, 3540.0)
        self.assertGreater(float(np.std(speeds)), 0.06)
        self.assertLess(float(np.std(speeds)), 0.16)
        self.assertGreater(lag_one_correlation(speeds), 0.9)
        self.assertLess(direction_reversal_ratio(speeds), 0.12)
        self.assertLess(float(np.quantile(np.abs(np.diff(speeds)), 0.95)), 0.08)

    def test_summary_rounds_pace_to_nearest_second(self) -> None:
        config = replace(self.config, distance_m=10300.0)
        simulator = Simulator(config)

        summary = simulator._summarize(simulator.simulate())

        self.assertEqual(summary["pace"], "5:54 /km")

    def test_heart_rate_has_warmup_drift_and_smooth_changes(self) -> None:
        heart_rates = np.asarray(
            [point.heart_rate for point in self.points],
            dtype=float,
        )

        self.assertAlmostEqual(float(np.mean(heart_rates)), 152.0, delta=0.5)
        self.assertGreater(
            float(np.mean(heart_rates[-300:])),
            float(np.mean(heart_rates[:300])) + 10.0,
        )
        self.assertGreater(float(np.std(heart_rates)), 4.0)
        self.assertLess(float(np.std(heart_rates)), 10.0)
        self.assertGreater(lag_one_correlation(heart_rates), 0.95)
        self.assertLess(direction_reversal_ratio(heart_rates), 0.12)
        self.assertLessEqual(
            float(np.quantile(np.abs(np.diff(heart_rates)), 0.95)),
            2.0,
        )

    def test_cadence_tracks_speed_without_white_noise(self) -> None:
        cadences = np.asarray(
            [point.cadence for point in self.points],
            dtype=float,
        )

        self.assertAlmostEqual(float(np.mean(cadences)), 172.0, delta=0.5)
        self.assertGreater(float(np.std(cadences)), 1.5)
        self.assertLess(float(np.std(cadences)), 4.0)
        self.assertGreater(lag_one_correlation(cadences), 0.8)
        self.assertLess(direction_reversal_ratio(cadences), 0.10)
        self.assertLessEqual(
            float(np.quantile(np.abs(np.diff(cadences)), 0.95)),
            3.0,
        )

    def test_fit_step_length_is_smooth_and_summary_targets_match(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = FitExporter().export(
                self.points,
                self.config,
                Path(temp_dir),
                "Realistic Treadmill",
            )
            stream = Stream.from_file(str(output_path))
            try:
                messages, errors = Decoder(stream).read(
                    enable_crc_check=True,
                    merge_heart_rates=False,
                )
            finally:
                stream.close()

        self.assertEqual(errors, [])
        records = messages["record_mesgs"]
        session = messages["session_mesgs"][0]
        step_lengths = np.asarray(
            [record["step_length"] for record in records],
            dtype=float,
        )

        self.assertEqual(session["sub_sport"], "treadmill")
        self.assertEqual(session["total_distance"], 10000.0)
        self.assertEqual(session["total_timer_time"], 3540.0)
        self.assertEqual(session["avg_heart_rate"], 152)
        self.assertGreaterEqual(session["avg_fractional_cadence"], 0.0)
        self.assertLess(session["avg_fractional_cadence"], 1.0)
        self.assertAlmostEqual(
            2
            * (
                session["avg_cadence"]
                + session.get("avg_fractional_cadence", 0)
            ),
            172.0,
            delta=0.5,
        )
        self.assertFalse(any("position_lat" in record for record in records))
        self.assertFalse(any("position_long" in record for record in records))
        self.assertGreater(float(np.std(step_lengths)), 20.0)
        self.assertLess(float(np.std(step_lengths)), 70.0)
        self.assertGreater(lag_one_correlation(step_lengths), 0.8)
        self.assertLess(direction_reversal_ratio(step_lengths), 0.20)
        self.assertLess(
            float(np.quantile(np.abs(np.diff(step_lengths)), 0.95)),
            25.0,
        )
