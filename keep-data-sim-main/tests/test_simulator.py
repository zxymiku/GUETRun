from dataclasses import replace
from unittest import TestCase

from keep_data_sim.config.schema import SimConfig
from keep_data_sim.core.simulator import Simulator
from keep_data_sim.utils.validation import validate_config


class SimulatorTests(TestCase):
    def test_dry_run_returns_expected_summary_keys(self) -> None:
        summary = Simulator(SimConfig(distance_m=1000, seed=1)).dry_run()

        self.assertEqual(summary["sport"], "running")
        self.assertGreater(summary["distance_m"], 0)
        self.assertGreater(summary["num_points"], 0)

    def test_validation_rejects_invalid_split_ratio(self) -> None:
        config = SimConfig()
        invalid = replace(config, pace=replace(config.pace, negative_split_ratio=0))

        with self.assertRaisesRegex(ValueError, "Negative split ratio"):
            validate_config(invalid)
