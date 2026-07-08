from __future__ import annotations

from typing import Any, Callable

from app.connectors.base import NormalizedEntity, NormalizedProcurementRecord
from app.connectors.common.generic_mapper import FieldHints, map_flat_record

SOURCE_NAME = "gem"
SOURCE_LABEL = "Government e-Marketplace (GeM)"

# GeM order/bid feeds use a mix of order-, bid-, and catalogue-oriented column
# names across exports. Hints cover the common variants so more real records map
# cleanly (higher ingestion coverage) without a bespoke mapper per export shape.
_HINTS = FieldHints(
    title=(
        "product_name", "item_name", "item", "contract_title", "title",
        "category_name", "category", "description", "bid_title", "service_name",
    ),
    buyer=(
        "buyer_name", "buyer", "organisation", "organization", "ministry",
        "department", "office", "buyer_organisation", "consignee",
    ),
    reference=(
        "contract_no", "contract_number", "order_no", "order_number",
        "bid_no", "bid_number", "reference", "gem_contract_id", "id",
    ),
    value=(
        "total_value", "contract_value", "order_value", "gross_amount",
        "value", "amount", "unit_price",
    ),
    published=(
        "contract_date", "order_date", "generated_date", "bid_end_date",
        "published", "created_date",
    ),
    closing=("bid_end_date", "bid_submission_end", "closing_date", "offer_validity"),
    supplier=("seller_name", "seller", "supplier", "vendor", "awarded_to", "service_provider"),
    supplier_reg=("seller_gstin", "gstin", "seller_id", "seller_pan", "udyam"),
    award_value=("total_value", "order_value", "contract_value", "gross_amount"),
    award_date=("contract_date", "order_date"),
    category=("category_name", "category", "product_category", "service_category"),
    location=("delivery_state", "state", "buyer_state", "consignee_state", "location"),
)


def map_record(
    raw_record: dict[str, Any],
    entity_extractor: Callable[[NormalizedProcurementRecord], list[NormalizedEntity]],
) -> NormalizedProcurementRecord:
    return map_flat_record(
        raw_record,
        source_name=SOURCE_NAME,
        reference_prefix="GEM",
        entity_extractor=entity_extractor,
        hints=_HINTS,
        currency_default="INR",
    )
