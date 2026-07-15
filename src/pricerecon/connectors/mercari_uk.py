"""Mercari UK connector using FlareSolverr + HTML parsing."""

from __future__ import annotations

from pricerecon.connectors.template_connector import TemplateConnector


class MercariUKConnector(TemplateConnector):
    template_name = "mercari"
    connector_id_override = "mercari_uk"
