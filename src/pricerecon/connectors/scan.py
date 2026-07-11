"""Scan connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class ScanConnector(TemplateConnector):
    template_name = "scan"
    connector_id_override = "scan"
