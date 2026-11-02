"""Abstract base class for exporters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from keep_data_sim.config.schema import SimConfig
from keep_data_sim.core.types import TrackPoint


class Exporter(ABC):
    """Export track points to a file format."""

    @abstractmethod
    def export(
        self,
        points: list[TrackPoint],
        config: SimConfig,
        output_dir: Path,
        title: str,
    ) -> Path:
        """Export track points and return the output file path."""
        ...
