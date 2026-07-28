"""CCL connector with truthful Cloudflare-blocked degraded behavior.

CCL has hardened Cloudflare protection that exceeds Byparr bypass capabilities.
Direct HTTP returns domain-wide 403. Byparr anti-bot route times out (>120s).
AO/Scan/Box connectors work via Byparr, confirming infrastructure health.

See diagnosis: TASK-XXXX (per-connector evidence for Cloudflare protection escalation).
"""

from __future__ import annotations

from typing import Any

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import NormalizedListing, SourceType


class CclConnector(BaseConnector):
    """Connector for CCL (Cloudflare-blocked).

    CCL has hardened Cloudflare protection that exceeds Byparr capabilities.
    This connector fails fast with a truthful degraded state instead of
    timing out after >120 seconds of bypass attempts.
    """

    CONNECTOR_ID = "ccl"
    BASE_URL = "https://www.cclonline.com"
    RETAILER_NAME = "CCL"
    WAF_DESCRIPTION = "hardened Cloudflare protection (HTTP 403 domain-wide)"
    WAF_EVIDENCE = (
        "Direct HTTP returns Cloudflare 403 'Just a moment...' challenge; "
        "Byparr anti-bot route times out (>120s) on CCL; "
        "AO/Scan/Box connectors work via Byparr, confirming infrastructure health"
    )
    DIAGNOSIS_TASK = "TASK-XXXX"

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

        This connector cannot return listings due to source-side Cloudflare
        protection that exceeds Byparr bypass capabilities. The degraded error
        includes diagnostic details for observability.
        """
        raise ConnectorDegradedError(
            status=ConnectorStatus.bot_blocked,
            message=(
                f"{self.RETAILER_NAME} is blocked by {self.WAF_DESCRIPTION}. "
                "The site returns HTTP 403 to direct requests and Byparr "
                "anti-bot route times out (>120s). This hardened protection "
                "exceeds current bypass capabilities."
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
