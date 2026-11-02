from __future__ import annotations

from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from keep_data_sim.cli import build_shift_fit_parser, main
from keep_data_sim.fit_shift import FitShiftResult, parse_local_start_time


class ShiftFitCliTests(TestCase):
    def test_parser_accepts_required_arguments_and_beijing_default(self) -> None:
        parser = build_shift_fit_parser()

        args = parser.parse_args([
            "original.fit",
            "--start-time",
            "2026-07-24 07:30:00",
        ])

        self.assertEqual(args.input, "original.fit")
        self.assertEqual(args.start_time, "2026-07-24 07:30:00")
        self.assertEqual(args.timezone, "Asia/Shanghai")
        self.assertIsNone(args.output)

    @patch("keep_data_sim.cli.shift_fit_start_time")
    def test_main_dispatches_shift_fit_command(self, shift_mock) -> None:
        new_start = parse_local_start_time("2026-07-24 07:30:00")
        shift_mock.return_value = FitShiftResult(
            input_path=Path("original.fit"),
            output_path=Path("modified.fit"),
            old_start=parse_local_start_time("2026-06-01 08:00:00"),
            new_start=new_start,
            delta=new_start - parse_local_start_time("2026-06-01 08:00:00"),
            message_count=10,
        )

        main([
            "shift-fit",
            "original.fit",
            "--start-time",
            "2026-07-24 07:30:00",
            "--output",
            "modified.fit",
        ])

        shift_mock.assert_called_once_with(
            "original.fit",
            new_start,
            "modified.fit",
            timezone_name="Asia/Shanghai",
        )
