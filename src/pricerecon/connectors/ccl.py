"""CCL connector using the configured Cloudflare challenge recovery lane."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class CclConnector(TemplateConnector):
    """CCL search connector with bounded FlareSolverr recovery."""

    template_name = "ccl"
    connector_id_override = "ccl"
