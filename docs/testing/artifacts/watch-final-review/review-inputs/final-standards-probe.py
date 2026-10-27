"""Read-only-source review probes; original synthetic values, guarded temporary DB only."""
import asyncio
import copy
import json
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch
from tests.monitoring.harness import MonitoringHarness

async def main():
    storage = Path(mkdtemp(prefix='pricerecon-offline-standards-'))
    (storage / '.offline-monitoring').write_text('ticket01-test-storage\n')
    results = {'storage': str(storage), 'synthetic': True, 'adapter_probes': []}
    with MonitoringHarness(storage_root=storage) as harness:
        from pricerecon import connectors
        from pricerecon.connectors.evidence import receipt
        from pricerecon.connectors.shopify_evidence import shopify_evidence
        from pricerecon.connectors.ebay_evidence import browse_evidence
        from pricerecon.core.discovery import execute_discovery
        from pricerecon.core.collection_policy import operating_policy
        from pricerecon.core.collection_transport import debit_resources
        from pricerecon.models import NormalizedListing, SourceType
        from pricerecon.models.discovery import DiscoveryRequest, DiscoveryAdmission
        from pricerecon.models.source_evidence import EvidenceUse
        from pricerecon.models.qualification import safe_pointer
        from pricerecon.core.rate_limiter import DurableAdmission
        use = EvidenceUse(permission_reference='original-review-fixture', retention='synthetic')
        admission = DiscoveryAdmission(mode='offline_verification', policy_reference='standards-probe', permission_reference='original-fixtures', activation_reference='guarded-child')
        cases = [
            ('shopify', shopify_evidence, {'products': [{'id': 1, 'handle': 'synthetic', 'title': 'Synthetic watch', 'options': [{'name': 'dial', 'position': 1}], 'variants': [{'id': 11, 'price': '50', 'currency': 'GBP', 'option1': 'blue'}, {'id': 12, 'price': '60', 'currency': 'GBP', 'option1': 'green'}]}]}),
            ('ebay', browse_evidence, {'itemSummaries': [{'itemId': 'one', 'title': 'Synthetic watch one', 'itemWebUrl': 'https://example.test/one', 'price': {'value': '50', 'currency': 'GBP'}}, {'itemId': 'two', 'title': 'Synthetic watch two', 'itemWebUrl': 'https://example.test/two', 'price': {'value': '60', 'currency': 'GBP'}}]})
        ]
        policy = type(harness.test_policy).model_validate({**harness.test_policy.model_dump(), 'provider_request_caps': {name: {'limit': 1000, 'tracking_reserve': 0} for name in ['cex', 'shopify', 'ebay']}})
        with operating_policy(policy):
            async with harness.session() as (client, _):
                for source, adapter, control in cases:
                    variants = [('control', copy.deepcopy(control)), ('bad_numeric_claim', copy.deepcopy(control))]
                    if source == 'shopify':
                        variants[1][1]['products'][0]['variants'][1]['price'] = '1e101'
                        long_option = copy.deepcopy(control)
                        long_option['products'][0]['variants'][1]['option1'] = 'x' * 501
                        variants.append(('bad_text_claim', long_option))
                    else:
                        variants[1][1]['itemSummaries'][1]['price']['value'] = '1e101'
                    for name, payload in variants:
                        def adapted():
                            capture = receipt('synthetic-review', use, [])
                            return adapter(payload, 'https://example.test', capture) if source == 'shopify' else adapter(payload, capture)
                        probe = {'source': source, 'case': name}
                        try:
                            report = adapted()
                            probe['direct_count'] = len(report.listings)
                        except Exception as exc:
                            probe['direct_error'] = type(exc).__name__
                            probe['direct_error_detail'] = str(exc)
                        class ControlledAdapter:
                            collection_accounting = 'controlled_v1'
                            async def initialize(self): pass
                            async def cleanup(self): pass
                            async def search_with_evidence(self, query, filters=None):
                                debit_resources(requests=1, pages=1)
                                return adapted()
                        with patch.object(connectors, 'discover_connectors', lambda: {source: ControlledAdapter}):
                            capture = await execute_discovery(DiscoveryRequest(query='synthetic', sources=[{'connector': source}]), admission=admission)
                        probe['normal_outcomes'] = [o.model_dump(mode='json') for o in capture.outcomes]
                        results['adapter_probes'].append(probe)
                        harness.clock.advance()
                urls = ['https://example.test/watch?access_token=SYNTHETIC', 'https://example.test/watch?client_secret=SYNTHETIC', 'https://example.test/watch?X-Amz-Credential=SYNTHETIC&X-Amz-Signature=SYNTHETIC']
                results['safe_pointer'] = [{'input': url, 'output': safe_pointer(url)} for url in urls]
                url = urls[1]
                harness.outcomes['cex'] = [NormalizedListing(source='cex', source_type=SourceType.RETAILER, source_listing_id='credential-query-fixture', title_raw='Synthetic lead', price='50', currency='GBP', url=url, timestamp_seen=harness.clock.now)]
                # Return the harness registry to prove the normal persistence/API path.
                await execute_discovery(DiscoveryRequest(query='synthetic', sources=[{'connector': 'cex'}]), admission=admission)
                body = (await client.get('/api/discovery/watches')).json()
                candidate = next(c for c in body['candidates'] if c['source_listing_id'] == 'credential-query-fixture')
                results['persisted_candidate_url'] = candidate['url']
                results['persisted_evidence_pointers'] = [c['pointer'] for c in candidate['evidence']]
                results['blocked_edges'] = harness.blocked_edges
    print(json.dumps(results, indent=2))

asyncio.run(main())
