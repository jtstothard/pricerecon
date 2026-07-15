"""Very.co.uk connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class VeryUKConnector(TemplateConnector):
    template_name = "very"
    connector_id_override = "very_uk"
