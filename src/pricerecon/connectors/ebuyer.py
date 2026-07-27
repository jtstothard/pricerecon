"""Ebuyer template connector marker."""

from .template_connector import TemplateConnector


class EbuyerConnector(TemplateConnector):
    """Template connector for Ebuyer search results."""

    template_name = "ebuyer"
