"""Scan connector with TemplateConnector and Camofox support."""

from pricerecon.connectors.template_connector import TemplateConnector

class ScanConnector(TemplateConnector):
    """Scan.co.uk connector using TemplateConnector with Camofox bypass."""

    template_name = "scan"

__all__ = ["ScanConnector"]