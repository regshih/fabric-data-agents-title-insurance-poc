# Direct Lake Execute Queries resolution

Test date: 2026-09-06

The Power BI Execute Queries endpoint originally returned HTTP 400 without a response body whenever DAX touched the custom `title_iq_sm` Direct Lake model. This was a secondary semantic-model validation path and did not affect Fabric Data Agent MCP calls, which query their configured Lakehouse or Ontology sources independently.

## Isolation

- Fabric tenant setting `DatasetExecuteQueries` is enabled.
- A model-independent query, `EVALUATE ROW("x", 1)`, returned `1`.
- Queries against `title_order` or model measures returned bodyless HTTP 400.
- The dataset existed, reported Direct Lake target storage mode `Abf`, and exposed the intended OneLake datasource.

## Fix

- Removed `schemaName: "dbo"` from entity partitions because the source is a non-schema Lakehouse.
- Added `[HierarchicalNavigation=true]` to the OneLake `AzureStorage.DataLake` expression.
- Changed definition updates to `updateMetadata=false`; the update payload intentionally has no `.platform` part.
- Triggered and completed a Direct Lake framing/refresh operation.

## Validation

- `EVALUATE TOPN(1, 'title_order')` returned `ORDER000001` and its mapped columns.
- `EVALUATE ROW("OpenTitleOrders", [Open Title Orders], "AtRiskOrders", [At-Risk Orders])` returned `OpenTitleOrders = 3246` and `AtRiskOrders = 349`.

The endpoint is now working against the model. The earlier bodyless 400 meant that the API accepted the request but the semantic engine could not activate/query the model binding; it was not an indication that Data Agent MCP was failing.
