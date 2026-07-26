"""Currys.co.uk connector using TemplateConnector and FlareSolverr."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class CurrysConnector(TemplateConnector):
    """Currys.co.uk connector using TemplateConnector with FlareSolverr."""

    template_name = "currys"
    connector_id_override = "currys"
