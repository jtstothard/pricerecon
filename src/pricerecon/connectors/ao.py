"""AO.com connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class AOConnector(TemplateConnector):
    template_name = "ao"
    connector_id_override = "ao"
