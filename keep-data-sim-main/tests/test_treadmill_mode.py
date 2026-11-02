from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from garmin_fit_sdk import Decoder, Stream

from keep_data_sim.cli import build_config, build_parser
from keep_data_sim.config.schema import PaceConfig, SimConfig
from keep_data_sim.core.simulator import Simulator
from keep_data_sim.export.fit_exporter import FitExporter
from keep_data_sim.utils.validation import validate_config


class TreadmillModeTests(TestCase):
    def setUp(self) -> None:
        self.config = SimConfig(
            treadmill=True,
            distance_m=1000.0,
            start_time=datetime(2026, 7, 30, 1, 0, tzinfo=timezone.utc),
            pace=PaceConfig(
                strategy="constant",
                avg_pace_min_per_km=6.0,
                warmup_duration_s=0.0,
            ),
            output_formats=("fit",),
            seed=20260730,
        )

    def test_cli_treadmill_defaults_to_fit_only(self) -> None:
        args = build_parser().parse_args(["--treadmill"])

        config = build_config(args)

        self.assertTrue(config.treadmill)
        self.assertEqual(config.output_formats, ("fit",))

    def test_validation_rejects_non_running_treadmill(self) -> None:
        config = replace(self.config, sport="cycling")

        with self.assertRaisesRegex(ValueError, "running"):
            validate_config(config)

    def test_validation_rejects_treadmill_gpx(self) -> None:
        config = replace(self.config, output_formats=("gpx",))

        with self.assertRaisesRegex(ValueError, "FIT"):
            validate_config(config)

    def test_simulator_uses_one_second_treadmill_timeline(self) -> None:
        simulator = Simulator(self.config)

        with patch.object(
            simulator,
            "_generate_route",
            side_effect=AssertionError("route generation must not be used"),
        ):
            points = simulator.simulate()

        duration = (points[-1].timestamp - points[0].timestamp).total_seconds()
        self.assertEqual(len(points), 361)
        self.assertAlmostEqual(points[-1].distance, 1000.0, places=3)
        self.assertAlmostEqual(duration, 360.0, places=3)
        self.assertEqual({point.latitude for point in points}, {39.9042})
        self.assertEqual({point.longitude for point in points}, {116.4074})
        self.assertEqual(len({point.elevation for point in points}), 1)
        self.assertEqual(simulator._summarize(points)["mode"], "treadmill")

    def test_treadmill_has_no_floating_point_tail_record(self) -> None:
        config = replace(self.config, distance_m=10000.0)

        points = Simulator(config).simulate()

        self.assertEqual(len(points), 3601)
        self.assertEqual(points[-1].distance, 10000.0)
        self.assertEqual(
            (points[-1].timestamp - points[-2].timestamp).total_seconds(),
            1.0,
        )

    def test_fit_export_has_treadmill_sub_sport_and_no_gps(self) -> None:
        points = Simulator(self.config).simulate()
        with TemporaryDirectory() as temp_dir:
            output_path = FitExporter().export(
                points,
                self.config,
                Path(temp_dir),
                "Treadmill Test",
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
        self.assertEqual(messages["sport_mesgs"][0]["sub_sport"], "treadmill")
        lap = messages["lap_mesgs"][0]
        session = messages["session_mesgs"][0]
        self.assertEqual(lap["sub_sport"], "treadmill")
        self.assertEqual(session["sub_sport"], "treadmill")
        self.assertEqual(session["total_distance"], 1000.0)
        self.assertEqual(session["total_timer_time"], 360.0)

        records = messages["record_mesgs"]
        self.assertFalse(any("position_lat" in record for record in records))
        self.assertFalse(any("position_long" in record for record in records))
        self.assertFalse(any("altitude" in record for record in records))
        self.assertTrue(all("step_length" in record for record in records))
        self.assertAlmostEqual(
            2
            * (
                session["avg_cadence"]
                + session.get("avg_fractional_cadence", 0)
            ),
            170.0,
            delta=1.0,
        )
        self.assertAlmostEqual(session["avg_step_length"], 980.4, delta=10.0)


if __name__ == "__main__":
    import unittest

    unittest.main()
