from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from garmin_fit_sdk import Decoder, Encoder, Stream
from garmin_fit_sdk.util import (
    convert_datetime_to_timestamp,
    convert_timestamp_to_datetime,
)

from keep_data_sim.fit_binary_shift import shift_fit_binary_start_time
from keep_data_sim.fit_shift import parse_local_start_time


class BinaryFitShiftTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.input_path = self.root / "original.fit"
        self.original_start = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
        self._write_activity(self.input_path, self.original_start)

    def test_preserves_structure_and_shifts_utc_and_local_times(self) -> None:
        output_path = self.root / "preserved.fit"
        new_start = parse_local_start_time("2026-07-24 07:30:00")
        original_bytes = self.input_path.read_bytes()

        result = shift_fit_binary_start_time(
            self.input_path,
            new_start,
            output_path,
            timezone_name="Asia/Shanghai",
        )
        output_bytes = output_path.read_bytes()
        messages, errors = self._decode(output_path)

        self.assertEqual(errors, [])
        self.assertEqual(len(output_bytes), len(original_bytes))
        self.assertEqual(output_bytes[:14], original_bytes[:14])
        self.assertEqual(result.message_count, 6)
        self.assertGreaterEqual(result.patched_field_count, 8)
        self.assertEqual(messages["session_mesgs"][0]["start_time"], new_start)
        self.assertEqual(len(messages["record_mesgs"]), 2)
        self.assertEqual(messages["record_mesgs"][1]["distance"], 250.0)

        activity = messages["activity_mesgs"][0]
        local_clock = convert_timestamp_to_datetime(activity["local_timestamp"])
        self.assertEqual(
            local_clock,
            datetime(2026, 7, 24, 7, 31, tzinfo=timezone.utc),
        )
        self.assertEqual(
            activity["local_timestamp"]
            - convert_datetime_to_timestamp(activity["timestamp"]),
            8 * 60 * 60,
        )

    @staticmethod
    def _write_activity(path: Path, start: datetime) -> None:
        encoder = Encoder()
        encoder.on_mesg(
            0,
            {
                "type": 4,
                "manufacturer": 1,
                "product": 0,
                "time_created": start,
                "serial_number": 123,
            },
        )
        encoder.on_mesg(
            20,
            {
                "timestamp": start,
                "position_lat": 0,
                "position_long": 0,
                "distance": 0.0,
            },
        )
        encoder.on_mesg(
            20,
            {
                "timestamp": start + timedelta(seconds=60),
                "position_lat": 1000,
                "position_long": 1000,
                "distance": 250.0,
            },
        )
        summary = {
            "timestamp": start + timedelta(seconds=60),
            "start_time": start,
            "total_elapsed_time": 60.0,
            "total_timer_time": 60.0,
            "total_distance": 250.0,
            "sport": 1,
        }
        encoder.on_mesg(19, dict(summary))
        encoder.on_mesg(18, {**summary, "num_laps": 1})
        encoder.on_mesg(
            34,
            {
                "timestamp": start + timedelta(seconds=60),
                "local_timestamp": convert_datetime_to_timestamp(
                    start + timedelta(hours=8, seconds=60)
                ),
                "total_timer_time": 60.0,
                "num_sessions": 1,
                "event": 26,
                "event_type": 1,
            },
        )
        path.write_bytes(encoder.close())

    @staticmethod
    def _decode(path: Path) -> tuple[dict, list]:
        stream = Stream.from_file(str(path))
        try:
            return Decoder(stream).read(enable_crc_check=True, merge_heart_rates=False)
        finally:
            stream.close()
