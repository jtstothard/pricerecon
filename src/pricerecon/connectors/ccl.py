"""CCL connector from direct HTML fetch using selectors."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class CclConnector(TemplateConnector):
    template_name = "ccl"
    connector_id_override = "ccl"
