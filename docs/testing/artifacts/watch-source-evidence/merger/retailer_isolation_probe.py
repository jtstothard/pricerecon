"""Independent normal execution/API probe: one malformed variant beside valid siblings.

Run each mode in a fresh process. Original synthetic HTTP data only, no app import
before MonitoringHarness, no replacement adapter or private database assertions.
"""
import asyncio
import json
from pathlib import Path
import sys
from unittest.mock import patch

import httpx
from tests.monitoring.harness import MonitoringHarness
from tests.monitoring.source_evidence_workflows import admission, retailer_fixture
from tests.monitoring.workflows import get

OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(__file__).resolve().parent
MODE = sys.argv[1]


async def main():
    with MonitoringHarness() as harness, retailer_fixture(harness):
        from pricerecon.connectors import shopify
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.models.discovery import DiscoveryRequest

        original_client = shopify.collection_http_client

        def client_factory(**kwargs):
            client = original_client(**kwargs)
            original_handler = client._transport.handler

            def handler(request):
                response = original_handler(request)
                if MODE == 'malformed' and request.url.path.endswith('/products.json'):
                    payload = response.json()
                    payload['products'][0]['variants'].append({
                        'id': 203, 'option1': 'malformed', 'option2': 'FKM',
                        'price': 'not-money', 'currency': 'GBP', 'available': True,
                    })
                    return httpx.Response(200, json=payload)
                return response

            # Mutate only the controlled external HTTP transport, preserving the
            # production event-hook client and all shared admission accounting.
            client._transport = httpx.MockTransport(handler)
            return client

        policy = type(harness.test_policy).model_validate({
            **harness.test_policy.model_dump(),
            'provider_request_caps': {'shopify': {'limit': 20, 'tracking_reserve': 0}},
        })
        with patch.object(shopify, 'collection_http_client', client_factory), operating_policy(policy):
            async with harness.session() as (client, _):
                await execute_discovery(DiscoveryRequest(query='SN0144', sources=[{
                    'connector': 'shopify', 'config': {
                        'base_url': 'https://www.sanmartin.watch',
                        'evidence_use': {'permission_reference': 'original-fixture', 'retention': 'synthetic'},
                    },
                }]), admission=admission())
                feed = await get(client, '/api/discovery/watches')
                collection = await get(client, '/api/discovery/collection')
                result = {
                    'mode': MODE, 'feed': feed, 'collection': collection,
                    'sends': harness.searches, 'notifications': harness.deliveries,
                    'blocked_edges': harness.blocked_edges,
                }
                (OUT / f'retailer-{MODE}.json').write_text(json.dumps(result, indent=2) + '\n')
                assert harness.blocked_edges == harness.deliveries == []
                assert len(harness.searches) == 2
                assert next(u['used'] for u in collection['usage'] if u['resource'] == 'requests') == 2
                candidates = {c['source_listing_id']: c for c in feed['candidates']}
                assert set(candidates) == {'201', '202'}, (MODE, feed['captures'][0]['outcomes'], set(candidates))
                assert candidates['201']['advertised_item_price'] == '110.00'
                assert candidates['202']['advertised_item_price'] == '180.00'
                assert candidates['202']['reported_currency'] is None
                assert all(c['public_delivered_total']['amount'] is None for c in candidates.values())
                assert feed['captures'][0]['outcomes'][0]['state'] == 'partial'
                capture = feed['captures'][0]['outcomes'][0]['source_evidence']
                assert capture['pages_captured'] == capture['page_limit'] == 1
                assert capture['item_limit'] == 250
                assert capture['inspected_count'] == 2
                assert next(u['used'] for u in collection['usage'] if u['resource'] == 'pages') == 2
                if MODE == 'malformed':
                    assert 'invalid_variant:0:2' in feed['captures'][0]['outcomes'][0]['source_evidence']['issues']
                print(MODE, 'passed: valid variants and independent prices retained; no qualification, escape or notification')


if __name__ == '__main__':
    asyncio.run(main())
