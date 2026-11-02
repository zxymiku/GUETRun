from datetime import timezone
from unittest import TestCase

from keep_data_sim.cli import build_config, build_parser, parse_pace


class CliTests(TestCase):
    def test_parse_pace_accepts_minute_second_format(self) -> None:
        self.assertEqual(parse_pace("5:30"), 5.5)

    def test_parse_pace_accepts_decimal_minutes(self) -> None:
        self.assertEqual(parse_pace("4.75"), 4.75)

    def test_build_config_parses_waypoints_and_start_time(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--route-type",
            "waypoint",
            "--waypoints",
            "39.0,116.0;39.1,116.1",
            "--start-time",
            "2026-06-16 00:00:00",
        ])

        config = build_config(args)

        self.assertEqual(config.route.waypoints, ((39.0, 116.0), (39.1, 116.1)))
        self.assertEqual(config.start_time.tzinfo, timezone.utc)

    def test_build_config_rejects_unknown_route_type(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--route-type", "unknown"])
