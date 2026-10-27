"""Per-variant storefront observations without manufacturer or UK cost inference."""

from decimal import Decimal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError

from pricerecon.connectors.evidence import claim
from pricerecon.models import NormalizedListing, SourceType
from pricerecon.models.qualification import (
    EvidenceContext,
    EvidenceSearchReport,
    IdentityField,
    MerchantEvidenceReport,
    OfferField,
)
from pricerecon.models.source_evidence import SourceOfferEvidence, SourceReceipt


class StoreOption(BaseModel):
    name: str
    position: int = Field(ge=1, le=3)


class StoreVariant(BaseModel):
    id: int | str
    price: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    available: bool | None = None
    option1: str | None = None
    option2: str | None = None
    option3: str | None = None


class StoreProduct(BaseModel):
    id: int | str
    handle: str = Field(pattern=r"^[a-zA-Z0-9-]+$")
    title: str = Field(min_length=1)
    options: list[StoreOption] = Field(default_factory=list)
    variants: list[object] = Field(default_factory=list)


class StorePage(BaseModel):
    products: list[object]


def shopify_evidence(
    payload: object, base_url: str, capture: SourceReceipt
) -> EvidenceSearchReport:
    page = StorePage.model_validate(payload)
    capture.pages_captured, capture.page_limit = 1, 1
    capture.item_limit = 250
    capture.discovered_count = len(page.products)
    capture.completeness = "partial"
    capture.issues = [
        "single_250_product_page",
        "pagination_not_exhausted",
        "query_not_catalogue_filter",
    ]
    merchant = urlsplit(base_url).hostname or base_url
    listings, reports = [], []
    for index, raw in enumerate(page.products):
        try:
            product = StoreProduct.model_validate(raw)
        except ValidationError:
            capture.issues.append(f"invalid_product:{index}")
            continue
        for position, raw_variant in enumerate(product.variants):
            try:
                variant = StoreVariant.model_validate(raw_variant)
            except ValidationError:
                capture.issues.append(f"invalid_variant:{index}:{position}")
                continue
            options = {
                option.name.casefold(): value
                for option in product.options
                if (value := getattr(variant, f"option{option.position}")) is not None
            }
            pointer = f"{base_url}/products/{product.handle}?variant={variant.id}"
            context = EvidenceContext(
                scope="selected_variation",
                merchant_key=merchant,
                product_id=str(product.id),
                variation_id=str(variant.id),
                currency=variant.currency,
            )
            fields: list[tuple[IdentityField | OfferField, str]] = [("seller", merchant)]
            fields.extend(
                (name, options[name]) for name in ("movement", "dial", "strap") if name in options
            )
            if variant.price is not None:
                fields.append(("item_price", str(variant.price)))
            if variant.currency:
                fields.append(("currency", variant.currency))
            if variant.available is not None:
                fields.append(("availability", "in_stock" if variant.available else "out_of_stock"))
            claims = [
                claim(
                    capture,
                    subject="selection" if name in {"movement", "dial", "strap"} else "offer",
                    field=name,
                    value=value,
                    issuer=merchant,
                    issuer_kind="seller",
                    pointer=pointer,
                    locator=f"products[{index}].variants[{position}].{name}",
                    context=context,
                )
                for name, value in fields
            ]
            listings.append(
                NormalizedListing.model_validate(
                    {
                        "source": "shopify",
                        "source_type": SourceType.RETAILER,
                        "source_listing_id": str(variant.id),
                        "title_raw": product.title,
                        "price": variant.price,
                        "currency": variant.currency or "",
                        "url": pointer,
                        "timestamp_seen": capture.retrieved_at,
                    }
                )
            )
            reports.append(
                MerchantEvidenceReport(
                    source_listing_id=str(variant.id),
                    merchant_key=merchant,
                    product_id=str(product.id),
                    variation_id=str(variant.id),
                    currency=variant.currency,
                    claims=claims,
                    source_evidence=SourceOfferEvidence(
                        merchant_role=(
                            "independent_retailer"
                            if merchant in {"sanmartin.watch", "www.sanmartin.watch"}
                            else "retailer"
                        ),
                        selected_options=options,
                        selected_sku=str(variant.id),
                        price_scope="selected_variation",
                        seller_literal=merchant,
                        availability_literal=(
                            str(variant.available) if variant.available is not None else None
                        ),
                        missing_fields=[
                            "manufacturer_definition",
                            "UK_destination",
                            "purchase_quantity",
                            "availability_basis",
                            "dispatch_origin",
                            "UK_delivered_cost",
                            "history_rights",
                        ],
                    ),
                )
            )
    capture.inspected_count = len(listings)
    return EvidenceSearchReport(
        listings=listings,
        evidence=reports,
        source_evidence=capture,
        acquisition_state="partial",
        acquisition_reason="bounded_retailer_variants",
        completeness="partial",
    )
