import type { DiscoveryFeed, parseSourceOfferEvidence, parseSourceReceipt } from '../../lib/discovery'

export function SourceReceipt({ receipt }: { receipt: ReturnType<typeof parseSourceReceipt> }) {
  return <div className="source-receipt">
    <p>Route {receipt.route}{receipt.source_host && ` · ${receipt.source_host}`}. Retrieved {receipt.retrieved_at}; completeness {receipt.completeness}.</p>
    <p>Pages captured {receipt.pages_captured}; page limit {receipt.page_limit ?? 'unknown'}; item limit {receipt.item_limit ?? 'unknown'}; detail limit {receipt.detail_limit ?? 'unknown'}; discovered {receipt.discovered_count ?? 'unknown'}; inspected {receipt.inspected_count ?? 'unknown'}.
      {' '}Next page {receipt.next_page === null ? 'unknown' : receipt.next_page ? 'present' : 'not reported'}; content truncated {receipt.content_truncated === null ? 'unknown' : String(receipt.content_truncated)}.</p>
    <p>Capture {receipt.capture_id}. Use reference {receipt.use?.permission_reference ?? 'missing'}; retention {receipt.use?.retention ?? 'unqualified'}; history rights unqualified. Retrieval does not grant storage or current freshness.</p>
    <ul>{receipt.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>
    <p>Prerequisites: {receipt.prerequisites.join('; ')}.</p>
  </div>
}

export function SourceOfferEvidence({ evidence }: { evidence: ReturnType<typeof parseSourceOfferEvidence> }) {
  return <section className="source-offer-evidence">
    <h4>Observed source details — review required</h4>
    <p>Merchant role {evidence.merchant_role.replace(/_/g, ' ')}. Selected SKU {evidence.selected_sku ?? 'unknown'}; price scope {evidence.price_scope}. Reported selection and price scope do not establish a qualified binding.</p>
    <dl>{Object.entries(evidence.selected_options).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
    <p>Condition literal {evidence.condition_literal ?? 'unknown'}; buying modes {evidence.purchase_modes.join(', ') || 'unknown'}.</p>
    <p>Seller claim {evidence.seller_literal ?? 'unknown'}; destination {evidence.destination ?? 'unknown'} {evidence.destination_literal ?? ''}; purchase quantity {evidence.quantity ?? 'unknown'}.</p>
    <p>Availability claim {evidence.availability_literal ?? 'unknown'}; stock quantity {evidence.stock_quantity ?? 'unknown'}. These source claims do not certify selected-SKU availability.</p>
    <p>Shipping claim {evidence.shipping_claim ?? 'unknown'}; VAT-included claim {evidence.vat_included_claim ?? 'unknown'}. Missing charges remain unknown.</p>
    <dl>{Object.entries(evidence.other_price_claims).map(([name, value]) => <div key={name}><dt>{name.replace(/_/g, ' ')}</dt><dd>{value}</dd></div>)}</dl>
    <p>Missing evidence: {evidence.missing_fields.join('; ')}.</p>
  </section>
}

export function SourceCoverage({ feed }: { feed: DiscoveryFeed }) {
  return <details className="source-coverage discovery-coverage">
    <summary>Source access and evidence coverage ({feed.source_coverage.length} routes)</summary>
    <p>Accepted research roster, dated 27 October 2026. Every lane remains staged. Reviewed leads require exact selection, availability, destination, UK cost and source-use evidence before qualification.</p>
    {feed.cohort_gaps.map(gap => <p className="discovery-caution" key={gap}>{gap}</p>)}
    {feed.source_coverage.map(row => <section data-route={row.route} key={row.route}>
      <h3>{row.source} · {row.accepted_status.replace(/_/g, ' ')}</h3>
      <p>Family {row.family.replace(/_/g, ' ')}. {row.reason}</p>
      <p>Prerequisites: {row.prerequisites.join('; ')}.</p>
      <p>Latest recorded attempt: {row.last_outcome ? `${row.last_outcome.state.replace(/_/g, ' ')}; ${row.last_outcome.reason ?? 'no reason supplied'}; ${row.last_outcome.listing_count} leads` : 'not attempted; missing current evidence'}.</p>
      {row.last_outcome?.source_evidence && <SourceReceipt receipt={row.last_outcome.source_evidence} />}
      <p className="discovery-quiet">Decision: {row.decision_reference}</p>
    </section>)}
    <p>Collection also requires finite measured budgets, physical storage/WAL/log/backup limits, retention/deletion/restore qualification and a named maintenance owner. Fixture allowances do not supply these operating prerequisites.</p>
  </details>
}
