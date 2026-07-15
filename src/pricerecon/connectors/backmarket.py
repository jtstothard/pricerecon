"""Back Market connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class BackMarketConnector(TemplateConnector):
    template_name = "backmarket"
    connector_id_override = "backmarket"
