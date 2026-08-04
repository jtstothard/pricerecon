"""Base connector interface."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, Optional, cast

from pricerecon.connectors.external_browser import ExternalBrowserAdapter, ExternalBrowserResult
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

    def configure_external_browser(
        self,
        runtime_config: Mapping[str, Any],
        connector_config: Mapping[str, Any] | None = None,
    ) -> None:
        """Attach an explicitly selected external browser to this connector.

        Construction stays backwards compatible: a connector has no browser at
        all unless the shared registry resolves a named selection.  The watch
        executor calls this uniformly after construction, so strict connector
        constructors do not need backend-specific arguments.
        """
        self._external_browser = ExternalBrowserAdapter.from_config(
            runtime_config, connector_config
        )

    def has_external_browser(self) -> bool:
        """Return whether this connector has an explicit backend selection."""
        adapter = cast(ExternalBrowserAdapter | None, getattr(self, "_external_browser", None))
        return adapter is not None and bool(adapter._backends)

    async def navigate_external_browser(self, url: str) -> ExternalBrowserResult | None:
        """Navigate only through the configured shared adapter, never locally."""
        adapter = cast(ExternalBrowserAdapter | None, getattr(self, "_external_browser", None))
        if adapter is None or not adapter._backends:
            return None
        result = await adapter.navigate(url)
        self._last_external_browser_result = result
        return result

    @staticmethod
    def browser_result_detail(result: ExternalBrowserResult) -> dict[str, Any]:
        """Safe connector diagnostic payload for a browser acquisition result."""
        return {
            "selected_backend": result.selected_backend,
            "browser_degradation": result.degradation.value,
            "browser_attempts": [
                {"backend": attempt.backend, "degradation": attempt.degradation.value}
                for attempt in result.attempts
            ],
        }

    def annotate_browser_result(
        self, listings: list[NormalizedListing], result: ExternalBrowserResult
    ) -> list[NormalizedListing]:
        """Retain selected-backend evidence with browser-acquired listings."""
        detail = self.browser_result_detail(result)
        return [
            listing.model_copy(
                update={"variant_normalized": {**(listing.variant_normalized or {}), **detail}}
            )
            for listing in listings
        ]
