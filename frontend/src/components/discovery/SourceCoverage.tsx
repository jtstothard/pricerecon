import { DetailRows } from './DetailRows'
import type { DiscoveryFeed, parseSourceOfferEvidence, parseSourceReceipt } from '../../lib/discovery'

export function SourceReceipt({ receipt }: { receipt: ReturnType<typeof parseSourceReceipt> }) {
  return <div className="source-receipt">
    <DetailRows rows={[
      ['Coverage', receipt.completeness], ['Retrieved', receipt.retrieved_at],
      ['Pages captured', receipt.pages_captured], ['Discovered', receipt.discovered_count], ['Inspected', receipt.inspected_count],
    ]} />
    <ul>{receipt.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>
    <p>Prerequisites: {receipt.prerequisites.join('; ')}.</p>
    <details><summary>Technical evidence</summary>
    <p>Route {receipt.route}{receipt.source_host && ` · ${receipt.source_host}`}</p>
    <p>Pages captured {receipt.pages_captured}; page limit {receipt.page_limit ?? 'unknown'}; item limit {receipt.item_limit ?? 'unknown'}; detail limit {receipt.detail_limit ?? 'unknown'}; discovered {receipt.discovered_count ?? 'unknown'}; inspected {receipt.inspected_count ?? 'unknown'}.
      {' '}Next page {receipt.next_page === null ? 'unknown' : receipt.next_page ? 'present' : 'not reported'}; content truncated {receipt.content_truncated === null ? 'unknown' : String(receipt.content_truncated)}.</p>
    <p>Capture {receipt.capture_id}. Use reference {receipt.use?.permission_reference ?? 'missing'}; retention {receipt.use?.retention ?? 'unqualified'}; history rights unqualified. Retrieval does not grant storage or current freshness.</p>
    </details>
  </div>
}

export function SourceOfferEvidence({ evidence }: { evidence: ReturnType<typeof parseSourceOfferEvidence> }) {
  return <section className="source-offer-evidence">
    <h4>Source claims: review required</h4>
    <p>Merchant role {evidence.merchant_role.replace(/_/g, ' ')}. Selected SKU {evidence.selected_sku ?? 'unknown'}; price scope {evidence.price_scope}. Reported selection and price scope do not establish a qualified binding.</p>
    <dl>{Object.entries(evidence.selected_options).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
    <DetailRows rows={[
      ['Condition', evidence.condition_literal], ['Buying modes', evidence.purchase_modes.join(', ') || 'unknown'],
      ['Seller', evidence.seller_literal], ['Destination', `${evidence.destination ?? 'unknown'} ${evidence.destination_literal ?? ''}`],
      ['Quantity', evidence.quantity], ['Availability', evidence.availability_literal], ['Stock quantity', evidence.stock_quantity],
      ['Shipping', evidence.shipping_claim], ['VAT included', evidence.vat_included_claim],
    ]} />
    <p>Source claims do not certify selected-SKU availability. Missing charges remain unknown.</p>
    <dl>{Object.entries(evidence.other_price_claims).map(([name, value]) => <div key={name}><dt>{name.replace(/_/g, ' ')}</dt><dd>{value}</dd></div>)}</dl>
    <p>Missing evidence: {evidence.missing_fields.join('; ')}.</p>
  </section>
}

export function SourceCoverage({ feed }: { feed: DiscoveryFeed }) {
  return <details className="source-coverage discovery-coverage">
    <summary>Sources and gaps ({feed.source_coverage.length} routes)</summary>
    <p>Accepted research roster, dated 27 October 2026. Every lane remains staged. Reviewed leads require exact selection, availability, destination, UK cost and source-use evidence before qualification.</p>
    {feed.cohort_gaps.map(gap => <p className="discovery-caution" key={gap}>{gap}</p>)}
    {feed.source_coverage.map(row => <section data-route={row.route} key={row.route}>
      <h3>{row.source} · {row.accepted_status.replace(/_/g, ' ')}</h3>
      <p>{row.reason}</p>
      <p>Prerequisites: {row.prerequisites.join('; ')}.</p>
      <p>Latest recorded attempt: {row.last_outcome ? `${row.last_outcome.state.replace(/_/g, ' ')}; ${row.last_outcome.reason ?? 'no reason supplied'}; ${row.last_outcome.listing_count} leads` : 'not attempted; missing current evidence'}.</p>
      <details><summary>Acquisition details</summary>{row.last_outcome?.source_evidence && <SourceReceipt receipt={row.last_outcome.source_evidence} />}
      <details><summary>Technical evidence</summary><DetailRows rows={[['Family', row.family.replace(/_/g, ' ')], ['Decision', row.decision_reference]]} /></details></details>
    </section>)}
    <p>Collection also requires finite measured budgets, physical storage/WAL/log/backup limits, retention/deletion/restore qualification and a named maintenance owner. Fixture allowances do not supply these operating prerequisites.</p>
  </details>
}
