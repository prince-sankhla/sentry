# Prozorro Tender JSON Mapping

Source sample inspected:

`data/raw/prozorro/9bdb97bf94d649a593e4370ddd8e7ef0.json`

The downloaded JSON is a single tender object. Useful top-level keys include:

`id`, `tenderID`, `title`, `description`, `status`, `date`, `dateCreated`, `dateModified`, `value`, `procuringEntity`, `awards`, `contracts`, `documents`, `items`, `plans`.

## Tender

| JSON Field | Database Column | Notes |
|---|---|---|
| `tenderID` | `tenders.reference_number` | Public Prozorro tender reference, for example `UA-2026-06-29-011978-a`. Prefer this over raw `id` for the current unique reference column. |
| `title` | `tenders.title` | Direct mapping. |
| `description` | `tenders.description` | May be absent or `null`. |
| `procuringEntity.name` | `tenders.procuring_entity` | The sample uses `procuringEntity`, not `buyer`. This is the buyer/procuring organization name. |
| `value.amount` | `tenders.estimated_value` | Decimal amount. |
| `value.currency` | `tenders.currency` | The sample uses `UAH`; current model default is `INR`, so use the JSON currency when present. |
| `date` | `tenders.published_date` | Convert timestamp to date. `dateCreated` is also available if creation date is preferred. |
| `dateModified` | No current column | Useful source metadata, but no current model column. |
| `status` | No current column | Useful tender state, but no current model column. |
| `id` | No current column | Prozorro internal tender UUID-like identifier. Could be used to construct source URL or retained externally, but no current model column. |
| `https://public.api.openprocurement.org/api/2.5/tenders/{id}` | No current column | Requested `source_url`; can be derived from `id`, but no current model column. |

## Company

Companies can come from two places:

- Buyer/procuring organization: `procuringEntity`
- Winning supplier organization: `awards[].suppliers[]`

The current `companies` table is most directly useful for award suppliers.

| JSON Field | Database Column | Notes |
|---|---|---|
| `awards[].suppliers[].name` | `companies.name` | Winning company/supplier name. |
| `awards[].suppliers[].identifier.id` | `companies.registration_number` | Identifier value, for example EDRPOU/tax identifier. |
| `awards[].suppliers[].identifier.scheme` | No current column | Useful for interpreting `registration_number`, but no current model column. |
| `awards[].suppliers[].address` | No current column | Requested `address`; no current model column. Available subfields include `streetAddress`, `locality`, `region`, `postalCode`, `countryName`. |
| `procuringEntity.name` | No direct company role column | Buyer name is currently mapped to `tenders.procuring_entity`, not `companies.name`, to avoid mixing buyers and suppliers without a role field. |
| `procuringEntity.identifier.id` | No direct company role column | Buyer identifier exists in JSON, but current schema has no buyer company relationship. |
| `procuringEntity.address` | No current column | Buyer address exists in JSON, but current schema has no address column. |

## Award

| JSON Field | Database Column | Notes |
|---|---|---|
| Parent tender row | `awards.tender_id` | Foreign key to the corresponding `tenders.id` database UUID after the tender row exists. |
| Matching supplier company row | `awards.company_id` | Foreign key to the corresponding `companies.id` database UUID after the supplier company row exists. |
| `awards[].suppliers[0]` | `awards.company_id` via `companies` | Winning company is represented by supplier data. If multiple suppliers exist, each needs an explicit handling rule before import. |
| `awards[].value.amount` | `awards.award_value` | Decimal award amount. |
| `awards[].value.currency` | `awards.currency` | Use JSON currency when present. |
| `awards[].date` | `awards.award_date` | Convert timestamp to date. |
| `awards[].status` | No current column | Useful for filtering active/cancelled awards, but no current model column. |
| `awards[].id` | No current column | Prozorro award identifier, but no current model column. |

## Requested Field Summary

| Requested Field | JSON Field | Database Column |
|---|---|---|
| Tender title | `title` | `tenders.title` |
| Tender buyer | `procuringEntity.name` | `tenders.procuring_entity` |
| Tender amount | `value.amount` | `tenders.estimated_value` |
| Tender date | `date` or `dateCreated` | `tenders.published_date` |
| Tender status | `status` | No current column |
| Tender source URL | Derived from `id` | No current column |
| Company name | `awards[].suppliers[].name` | `companies.name` |
| Company identifier | `awards[].suppliers[].identifier.id` | `companies.registration_number` |
| Company address | `awards[].suppliers[].address` | No current column |
| Award winning company | `awards[].suppliers[]` | `awards.company_id` via `companies.id` |
| Award amount | `awards[].value.amount` | `awards.award_value` |
| Award date | `awards[].date` | `awards.award_date` |
