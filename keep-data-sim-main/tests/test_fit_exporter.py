from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from garmin_fit_sdk import Decoder, Stream
from garmin_fit_sdk.util import convert_datetime_to_timestamp

from keep_data_sim.config.schema import SimConfig
from keep_data_sim.core.types import TrackPoint
from keep_data_sim.export.fit_exporter import FitExporter


class FitExporterCompatibilityTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.start = datetime(2026, 7, 29, 22, 0, tzinfo=timezone.utc)
        self.end = self.start + timedelta(seconds=60)
        self.points = [
            TrackPoint(
                latitude=39.9042,
                longitude=116.4074,
                elevation=40.0,
                timestamp=self.start,
                speed=3.0,
                heart_rate=140,
                cadence=170,
                distance=0.0,
            ),
            TrackPoint(
                latitude=39.905,
                longitude=116.408,
                elevation=41.0,
                timestamp=self.end,
                speed=3.1,
                heart_rate=145,
                cadence=172,
                distance=180.0,
            ),
        ]

    def test_writes_complete_garmin_activity_structure(self) -> None:
        config = SimConfig(output_dir=str(self.root), output_formats=("fit",))

        output_path = FitExporter().export(
            self.points,
            config,
            self.root,
            "Garmin Compatible",
        )
        messages, errors, order = self._decode(output_path)

        self.assertEqual(errors, [])
        self.assertEqual(order, [0, 23, 12, 21, 20, 20, 21, 19, 18, 34])

        file_id = messages["file_id_mesgs"][0]
        self.assertEqual(file_id["manufacturer"], "development")
        self.assertEqual(file_id["product_name"], "Keep Data Simulator")

        creator = messages["device_info_mesgs"][0]
        self.assertEqual(creator["device_index"], "creator")
        self.assertEqual(creator["manufacturer"], "development")
        self.assertEqual(creator["product_name"], "Keep Data Simulator")

        events = messages["event_mesgs"]
        self.assertEqual(events[0]["timestamp"], self.start)
        self.assertEqual(events[0]["event"], "timer")
        self.assertEqual(events[0]["event_type"], "start")
        self.assertEqual(events[1]["timestamp"], self.end)
        self.assertEqual(events[1]["event"], "timer")
        self.assertEqual(events[1]["event_type"], "stop_all")

        activity = messages["activity_mesgs"][0]
        self.assertEqual(activity["timestamp"], self.end)
        self.assertEqual(
            activity["local_timestamp"]
            - convert_datetime_to_timestamp(activity["timestamp"]),
            8 * 60 * 60,
        )

        records = messages["record_mesgs"]
        self.assertAlmostEqual(
            2 * (records[0]["cadence"] + records[0]["fractional_cadence"]),
            170.0,
        )
        self.assertAlmostEqual(records[0]["step_length"], 1058.8, places=1)

        lap = messages["lap_mesgs"][0]
        session = messages["session_mesgs"][0]
        self.assertEqual(session["sub_sport"], "generic")
        self.assertEqual(session["first_lap_index"], 0)
        self.assertEqual(session["num_laps"], 1)
        for summary in (lap, session):
            self.assertEqual(summary["message_index"], 0)
            self.assertEqual(summary["start_time"], self.start)
            self.assertEqual(summary["timestamp"], self.end)
            self.assertEqual(summary["total_elapsed_time"], 60.0)
            self.assertEqual(summary["total_timer_time"], 60.0)
            self.assertEqual(summary["total_strides"], 86)
            self.assertAlmostEqual(summary["avg_step_length"], 1052.6, places=1)
            self.assertAlmostEqual(
                2
                * (
                    summary["avg_cadence"]
                    + summary["avg_fractional_cadence"]
                ),
                171.0,
            )

    def test_cycling_cadence_stays_in_rpm_without_step_length(self) -> None:
        cycling_points = [
            replace(self.points[0], cadence=85),
            replace(self.points[1], cadence=86),
        ]
        config = SimConfig(
            sport="cycling",
            output_dir=str(self.root),
            output_formats=("fit",),
        )

        output_path = FitExporter().export(
            cycling_points,
            config,
            self.root,
            "Cycling Cadence",
        )
        messages, errors, _ = self._decode(output_path)

        self.assertEqual(errors, [])
        first_record = messages["record_mesgs"][0]
        self.assertEqual(first_record["cadence"], 85)
        self.assertNotIn("step_length", first_record)
        self.assertAlmostEqual(messages["session_mesgs"][0]["avg_cadence"], 85)

    @staticmethod
    def _decode(path: Path) -> tuple[dict, list, list[int]]:
        order: list[int] = []
        stream = Stream.from_file(str(path))
        try:
            decoder = Decoder(stream)
            messages, errors = decoder.read(
                enable_crc_check=True,
                merge_heart_rates=False,
                mesg_listener=lambda number, message: order.append(number),
            )
            return messages, errors, order
        finally:
            stream.close()
