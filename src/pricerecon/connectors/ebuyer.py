"""Ebuyer connector from direct HTML fetch using selectors."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class EbuyerConnector(TemplateConnector):
    template_name = "ebuyer"
    connector_id_override = "ebuyer"
