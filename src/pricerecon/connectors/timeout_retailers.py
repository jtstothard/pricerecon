"""WAF-blocked retail connectors (Scan, Overclockers, Box, Currys).

These four retailers have been diagnosed with source-side WAF blocking causing
Byparr/FlareSolverr to timeout. All return HTTP 403 to direct requests and
present JavaScript challenges that prevent Playwright page load completion
within 60 seconds.

Instead of silent timeouts, these connectors raise ConnectorDegradedError with
status=bot_blocked and truthful error messages about the underlying WAF blocking.

See diagnosis: t_bd07a701 (per-connector evidence for source-side blocking).
"""

from __future__ import annotations

from typing import Any

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import NormalizedListing, SourceType


class TimeoutRetailerConnector(BaseConnector):
    """Connector for WAF-blocked retailers that cannot be scraped via Byparr.

    This connector fails fast with a truthful degraded state instead of
    timing out after 60 seconds of WAF challenges.
    """

    CONNECTOR_ID: str
    BASE_URL: str
    RETAILER_NAME: str

    @property
    def source_role(self) -> SourceType:
        return SourceType.RETAILER

    @property
    def connector_id(self) -> str:
        return self.CONNECTOR_ID

    async def initialize(self) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def search(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        """Always raises ConnectorDegradedError with bot_blocked status.

        This connector cannot return listings due to source-side WAF blocking.
        The degraded error includes diagnostic details for observability.
        """
        raise ConnectorDegradedError(
            status=ConnectorStatus.bot_blocked,
            message=(
                f"{self.RETAILER_NAME} is blocked by source-side WAF protection. "
                "The site returns HTTP 403 to direct requests and presents "
                "JavaScript challenges that exceed Byparr's 60-second timeout."
            ),
            connector_id=self.connector_id,
            detail={
                "root_cause": "WAF blocking (likely Cloudflare)",
                "evidence": "HTTP 403 responses, JavaScript challenges, Byparr timeouts at 60s",
                "diagnosis_task": "t_bd07a701",
                "remediation": "Consider CloakBrowser integration, residential proxies, or commercial scraping services",
                "url": self.BASE_URL,
            },
        )


class ScanConnector(TimeoutRetailerConnector):
    """Scan.co.uk connector (WAF-blocked)."""

    CONNECTOR_ID = "scan"
    BASE_URL = "https://www.scan.co.uk"
    RETAILER_NAME = "Scan"


class OverclockersConnector(TimeoutRetailerConnector):
    """Overclockers.co.uk connector (WAF-blocked)."""

    CONNECTOR_ID = "overclockers"
    BASE_URL = "https://www.overclockers.co.uk"
    RETAILER_NAME = "Overclockers"


class BoxConnector(TimeoutRetailerConnector):
    """Box.co.uk connector (WAF-blocked)."""

    CONNECTOR_ID = "box"
    BASE_URL = "https://www.box.co.uk"
    RETAILER_NAME = "Box"


class CurrysConnector(TimeoutRetailerConnector):
    """Currys.co.uk connector (WAF-blocked)."""

    CONNECTOR_ID = "currys"
    BASE_URL = "https://www.currys.co.uk"
    RETAILER_NAME = "Currys"
