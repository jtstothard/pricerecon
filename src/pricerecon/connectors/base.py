"""Base connector interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from pricerecon.models import NormalizedListing, SourceType


class BaseConnector(ABC):
    """Abstract base class for all connectors.

    Connectors implement search(query, filters) to return normalized listings.
    They also declare their source role (retailer, marketplace, signal).
    """

    @property
    @abstractmethod
    def source_role(self) -> SourceType:
        """Return the source type (retailer, marketplace, signal)."""

    @property
    def connector_id(self) -> str:
        """Return the connector identifier (e.g., 'ebay', 'cex')."""
        explicit = getattr(self, "CONNECTOR_ID", None)
        if explicit:
            return str(explicit)
        return self.__class__.__name__.lower().replace("connector", "")

    @abstractmethod
    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search the source for matching listings.

        Args:
            query: Search query string
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings
        """

    async def initialize(self) -> None:
        """Initialize the connector (auth setup, etc.). Optional."""

    async def cleanup(self) -> None:
        """Cleanup resources (close browser, etc.). Optional."""
