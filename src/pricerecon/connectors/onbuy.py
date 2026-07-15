"""OnBuy connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class OnBuyConnector(TemplateConnector):
    template_name = "onbuy"
    connector_id_override = "onbuy"
