"""Etsy connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class EtsyConnector(TemplateConnector):
    template_name = "etsy"
    connector_id_override = "etsy"
