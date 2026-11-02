from unittest import TestCase

from keep_data_sim.cli import build_config, build_parser
from keep_data_sim.config.schema import SimConfig
from keep_data_sim.utils.validation import validate_config


class TimezoneConfigTests(TestCase):
    def test_cli_defaults_to_shanghai_timezone(self) -> None:
        args = build_parser().parse_args([])

        config = build_config(args)

        self.assertEqual(config.timezone_name, "Asia/Shanghai")

    def test_cli_accepts_another_iana_timezone(self) -> None:
        args = build_parser().parse_args(["--timezone", "Europe/London"])

        config = build_config(args)

        self.assertEqual(config.timezone_name, "Europe/London")

    def test_validation_rejects_unknown_timezone(self) -> None:
        config = SimConfig(timezone_name="Not/A_Timezone")

        with self.assertRaisesRegex(ValueError, "Unknown timezone"):
            validate_config(config)
