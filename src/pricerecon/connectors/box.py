"""Box connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class BoxConnector(TemplateConnector):
    template_name = "box"
    connector_id_override = "box"
