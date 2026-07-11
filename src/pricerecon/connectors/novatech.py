"""Novatech connector from direct HTML fetch using selectors."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class NovatechConnector(TemplateConnector):
    template_name = "novatech"
    connector_id_override = "novatech"
