"""Depop connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class DepopConnector(TemplateConnector):
    template_name = "depop"
    connector_id_override = "depop"
