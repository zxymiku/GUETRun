from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from garmin_fit_sdk import Decoder, Encoder, Stream
from garmin_fit_sdk.util import convert_datetime_to_timestamp

from keep_data_sim.fit_shift import parse_local_start_time, shift_fit_start_time


class FitShiftTests(TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.input_path = self.root / "original.fit"
        self.original_start = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
        self._write_activity(self.input_path, self.original_start)

    def test_parse_local_start_time_converts_beijing_time_to_utc(self) -> None:
        parsed = parse_local_start_time("2026-07-24 07:30:00", "Asia/Shanghai")

        self.assertEqual(parsed, datetime(2026, 7, 23, 23, 30, tzinfo=timezone.utc))

    def test_shift_changes_all_activity_times_and_preserves_metrics(self) -> None:
        output_path = self.root / "modified.fit"
        new_start = parse_local_start_time("2026-07-24 07:30:00", "Asia/Shanghai")

        result = shift_fit_start_time(self.input_path, new_start, output_path)
        messages, errors = self._decode(output_path)

        self.assertEqual(errors, [])
        self.assertEqual(result.old_start, self.original_start)
        self.assertEqual(result.new_start, new_start)
        self.assertEqual(result.output_path, output_path)
        self.assertEqual(messages["session_mesgs"][0]["start_time"], new_start)
        self.assertEqual(
            messages["record_mesgs"][1]["timestamp"],
            new_start + timedelta(seconds=60),
        )
        self.assertEqual(messages["record_mesgs"][1]["distance"], 250.0)
        self.assertEqual(messages["record_mesgs"][1]["heart_rate"], 145)
        self.assertEqual(messages["session_mesgs"][0]["total_timer_time"], 60.0)
        expected_local_timestamp = convert_datetime_to_timestamp(
            datetime(2026, 7, 24, 7, 31, tzinfo=timezone.utc)
        )
        self.assertEqual(
            messages["activity_mesgs"][0]["local_timestamp"],
            expected_local_timestamp,
        )

    def test_default_output_is_created_beside_input(self) -> None:
        new_start = parse_local_start_time("2026-07-24 07:30:00", "Asia/Shanghai")

        result = shift_fit_start_time(self.input_path, new_start)

        self.assertEqual(result.output_path, self.root / "original_shifted.fit")
        self.assertTrue(result.output_path.exists())

    def test_refuses_to_overwrite_input(self) -> None:
        new_start = parse_local_start_time("2026-07-24 07:30:00", "Asia/Shanghai")

        with self.assertRaisesRegex(ValueError, "must be different"):
            shift_fit_start_time(self.input_path, new_start, self.input_path)

    def test_rejects_invalid_crc(self) -> None:
        corrupt_path = self.root / "corrupt.fit"
        data = bytearray(self.input_path.read_bytes())
        data[-1] ^= 0xFF
        corrupt_path.write_bytes(data)
        new_start = parse_local_start_time("2026-07-24 07:30:00", "Asia/Shanghai")

        with self.assertRaisesRegex(ValueError, "CRC"):
            shift_fit_start_time(corrupt_path, new_start)

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
                "speed": 4.0,
                "heart_rate": 140,
            },
        )
        encoder.on_mesg(
            20,
            {
                "timestamp": start + timedelta(seconds=60),
                "position_lat": 1000,
                "position_long": 1000,
                "distance": 250.0,
                "speed": 4.2,
                "heart_rate": 145,
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
                "local_timestamp": convert_datetime_to_timestamp(start + timedelta(hours=8, seconds=60)),
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
            decoder = Decoder(stream)
            return decoder.read(enable_crc_check=True)
        finally:
            stream.close()
