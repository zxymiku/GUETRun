"""Abstract base class for route generators."""

from __future__ import annotations

from abc import ABC, abstractmethod

from keep_data_sim.config.schema import RouteConfig


class RouteGenerator(ABC):
    """Generate a list of (lat, lon) coordinates forming a route."""

    @abstractmethod
    def generate(
        self,
        config: RouteConfig,
        distance_m: float,
        rng: object,
    ) -> list[tuple[float, float]]:
        """Return list of (lat, lon) pairs forming the route.

        Args:
            config: Route configuration.
            distance_m: Target total distance in meters.
            rng: numpy random Generator instance.

        Returns:
            Ordered list of (latitude, longitude) coordinate pairs.
        """
        ...
