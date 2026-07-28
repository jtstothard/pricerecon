"""HotUKDeals connector using Camofox."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class HotUKDealsConnector(TemplateConnector):
    template_name = "hotukdeals"
    connector_id_override = "hotukdeals"