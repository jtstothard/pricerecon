"""Currys connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class CurrysConnector(TemplateConnector):
    template_name = "currys"
    connector_id_override = "currys"
