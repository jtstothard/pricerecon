"""Browse search fields are review leads, never default stock or selected SKUs."""

from decimal import Decimal

from pydantic import BaseModel, Field, ValidationError

from pricerecon.connectors.evidence import claim
from pricerecon.models import NormalizedListing, SourceType
from pricerecon.models.qualification import (
    EvidenceContext,
    EvidenceSearchReport,
    MerchantEvidenceReport,
    OfferField,
)
from pricerecon.models.source_evidence import SourceOfferEvidence, SourceReceipt


class BrowseMoney(BaseModel):
    value: Decimal = Field(ge=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


class BrowseSeller(BaseModel):
    username: str | None = None


class BrowseStock(BaseModel):
    estimatedAvailabilityStatus: str | None = None
    estimatedAvailableQuantity: int | None = Field(default=None, ge=0)


class BrowseDestination(BaseModel):
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")


class BrowseShipping(BaseModel):
    shippingCostType: str | None = None
    shippingCost: BrowseMoney | None = None


class BrowseItem(BaseModel):
    itemId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    itemWebUrl: str
    price: BrowseMoney | None = None
    currentBidPrice: BrowseMoney | None = None
    seller: BrowseSeller = Field(default_factory=BrowseSeller)
    condition: str | None = None
    conditionId: str | None = None
    buyingOptions: list[str] = Field(default_factory=list)
    estimatedAvailabilities: list[BrowseStock] = Field(default_factory=list)
    shipToLocationUsedForEstimate: BrowseDestination | None = None
    shippingOptions: list[BrowseShipping] = Field(default_factory=list)


class BrowsePage(BaseModel):
    itemSummaries: list[object] = Field(default_factory=list)
    next: str | None = None
    total: int | None = Field(default=None, ge=0)


def browse_evidence(payload: object, capture: SourceReceipt) -> EvidenceSearchReport:
    page = BrowsePage.model_validate(payload)
    capture.pages_captured, capture.page_limit = 1, 1
    capture.item_limit = 50
    capture.discovered_count = page.total
    capture.inspected_count = len(page.itemSummaries)
    capture.next_page = bool(page.next)
    capture.completeness = "partial" if page.next else "unknown"
    if page.next:
        capture.issues.append("next_page_not_followed")
    listings, reports = [], []
    for index, raw in enumerate(page.itemSummaries):
        try:
            item = BrowseItem.model_validate(raw)
            bid = "AUCTION" in item.buyingOptions
            price = item.currentBidPrice if bid else item.price
            context = EvidenceContext(
                scope="generic_listing",
                merchant_key="ebay",
                product_id=item.itemId,
                currency=price.currency if price else None,
            )
            fields: list[tuple[OfferField, str]] = []
            if item.seller.username:
                fields.append(("seller", item.seller.username))
            if item.condition:
                fields.append(("condition_description", item.condition))
            condition = {"1000": "new", "3000": "used", "2000": "refurbished"}.get(
                item.conditionId or ""
            )
            if condition:
                fields.append(("condition", condition))
            if item.buyingOptions == ["AUCTION"]:
                fields.append(("purchase_mode", "auction"))
            elif item.buyingOptions == ["FIXED_PRICE"]:
                fields.append(("purchase_mode", "buy_now"))
            statuses = {entry.estimatedAvailabilityStatus for entry in item.estimatedAvailabilities}
            if statuses == {"IN_STOCK"}:
                fields.append(("availability", "in_stock"))
            elif statuses == {"OUT_OF_STOCK"}:
                fields.append(("availability", "out_of_stock"))
            if price:
                fields.append(("item_price", str(price.value)))
                if price.currency:
                    fields.append(("currency", price.currency))
            claims = [
                claim(
                    capture,
                    subject="offer",
                    field=name,
                    value=value,
                    issuer=item.seller.username or "eBay seller unspecified",
                    issuer_kind="seller",
                    pointer=item.itemWebUrl,
                    locator=f"itemSummaries[{index}].{name}",
                    context=context,
                )
                for name, value in fields
            ]
            listing = NormalizedListing.model_validate(
                {
                    "source": "ebay",
                    "source_type": SourceType.MARKETPLACE,
                    "source_listing_id": item.itemId,
                    "title_raw": item.title,
                    "price": price.value if price else None,
                    "currency": (price.currency or "") if price else "",
                    "url": item.itemWebUrl,
                    "timestamp_seen": capture.retrieved_at,
                }
            )
            report = MerchantEvidenceReport(
                source_listing_id=item.itemId,
                merchant_key="ebay",
                product_id=item.itemId,
                currency=price.currency if price else None,
                claims=claims,
                source_evidence=SourceOfferEvidence(
                    merchant_role="marketplace",
                    price_scope="auction_bid" if bid else "parent_listing",
                    condition_literal=item.condition,
                    purchase_modes=item.buyingOptions,
                    seller_literal=item.seller.username,
                    destination=(
                        item.shipToLocationUsedForEstimate.country
                        if item.shipToLocationUsedForEstimate
                        else None
                    ),
                    availability_literal=next(iter(statuses)) if len(statuses) == 1 else None,
                    stock_quantity=(
                        item.estimatedAvailabilities[0].estimatedAvailableQuantity
                        if len(item.estimatedAvailabilities) == 1
                        else None
                    ),
                    shipping_claim="; ".join(
                        f"{option.shippingCostType or 'unknown'} {option.shippingCost.currency or 'unknown'} {option.shippingCost.value}"
                        for option in item.shippingOptions
                        if option.shippingCost
                    )
                    or None,
                    other_price_claims=(
                        {
                            "listing_price": str(item.price.value),
                            "listing_currency": item.price.currency or "unknown",
                        }
                        if bid and item.price
                        else {}
                    ),
                    missing_fields=[
                        "selected_variation",
                        "manufacturer_definition",
                        "UK_destination",
                        "UK_delivered_cost",
                        "history_rights",
                        "taxes_unknown",
                    ]
                    + ([] if statuses else ["availability"]),
                ),
            )
        except ValidationError:
            capture.issues.append(f"invalid_item:{index}")
            continue
        # Keep the listing/report pair atomic at the item boundary.
        listings.append(listing)
        reports.append(report)
    partial = bool(page.next or capture.issues)
    return EvidenceSearchReport(
        listings=listings,
        evidence=reports,
        source_evidence=capture,
        acquisition_state="partial" if partial else "success",
        acquisition_reason="bounded_browse_leads" if partial else None,
        completeness="partial" if partial else "unknown",
    )
