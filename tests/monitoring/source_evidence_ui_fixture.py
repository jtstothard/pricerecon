"""Original adapter payloads for the guarded discovery UI server."""

from .source_evidence_workflows import admission, browse_fixture, browser_fixture, retailer_fixture


async def populate(harness, comparison_policy=None):
    from pricerecon.core.collection_policy import operating_policy
    from pricerecon.core.discovery import execute_discovery
    from pricerecon.models.discovery import DiscoveryRequest

    policy = type(harness.test_policy).model_validate(
        {
            **harness.test_policy.model_dump(),
            "provider_request_caps": {
                source: {"limit": 20, "tracking_reserve": 0}
                for source in ("aliexpress", "ebay", "shopify")
            },
        }
    )
    use = {"permission_reference": "original-fixture", "retention": "synthetic"}
    with operating_policy(policy):
        for fixture, source, config, query in (
            (
                browser_fixture,
                "aliexpress",
                {"browser_max_products": 1, "evidence_use": use},
                "AD2066",
            ),
            (
                browse_fixture,
                "ebay",
                {"app_id": "synthetic", "cert_id": "synthetic", "evidence_use": use},
                "Casio OR Merkur",
            ),
            (
                retailer_fixture,
                "shopify",
                {"base_url": "https://www.sanmartin.watch", "evidence_use": use},
                "SN0144",
            ),
        ):
            with fixture(harness):
                await execute_discovery(
                    DiscoveryRequest(
                        query=query, sources=[{"connector": source, "config": config}]
                    ),
                    admission=admission(),
                    comparison_policy=comparison_policy,
                )
