"""WAF-blocked retail connectors (Scan, Overclockers, Box, Currys).

These four retailers have been diagnosed with source-side WAF blocking causing
Byparr/FlareSolverr to timeout. All return HTTP 403 to direct requests and
present JavaScript challenges that prevent Playwright page load completion
within 60 seconds.

Instead of silent timeouts, these connectors raise ConnectorDegradedError with
status=bot_blocked and truthful error messages about the underlying WAF blocking.

See diagnosis: ***REMOVED*** (per-connector evidence for source-side blocking).
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
    WAF_DESCRIPTION = "source-side WAF protection"
    WAF_EVIDENCE = (
        "HTTP 403 responses, JavaScript challenges, Byparr timeouts at 60s"
    )
    DIAGNOSIS_TASK = "***REMOVED***"

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
                f"{self.RETAILER_NAME} is blocked by {self.WAF_DESCRIPTION}. "
                "The site returns HTTP 403 to direct requests and presents "
                "JavaScript challenges that exceed Byparr's 60-second timeout."
            ),
            connector_id=self.connector_id,
            detail={
                "root_cause": self.WAF_DESCRIPTION,
                "evidence": self.WAF_EVIDENCE,
                "diagnosis_task": self.DIAGNOSIS_TASK,
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
    WAF_DESCRIPTION = "Cloudflare Turnstile WAF protection (HTTP 403)"
    WAF_EVIDENCE = (
        "Captured direct HTTP 403 and Turnstile challenge responses from "
        "Direct HTTP, Playwright, Camofox, and CloakBrowser transport tests"
    )
    DIAGNOSIS_TASK = "***REMOVED***"


class BoxConnector(TimeoutRetailerConnector):
    """Box.co.uk connector (WAF-blocked, no functional browser route)."""

    CONNECTOR_ID = "box"
    BASE_URL = "https://www.box.co.uk"
    RETAILER_NAME = "Box"


class CurrysConnector(TimeoutRetailerConnector):
    """Currys.co.uk connector (WAF-blocked)."""

    CONNECTOR_ID = "currys"
    BASE_URL = "https://www.currys.co.uk"
    RETAILER_NAME = "Currys"
