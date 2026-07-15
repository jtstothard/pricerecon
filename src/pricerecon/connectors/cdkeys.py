"""CDKeys connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class CDKeysConnector(TemplateConnector):
    template_name = "cdkeys"
    connector_id_override = "cdkeys"
