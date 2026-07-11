"""Overclockers connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class OverclockersConnector(TemplateConnector):
    template_name = "overclockers"
    connector_id_override = "overclockers"
