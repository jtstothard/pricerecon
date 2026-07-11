"""Aria connector from direct HTML fetch using selectors."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class AriaConnector(TemplateConnector):
    template_name = "aria"
    connector_id_override = "aria"
