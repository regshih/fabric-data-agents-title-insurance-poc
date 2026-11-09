from __future__ import annotations

import base64
import json
import uuid

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, read_state, write_state


def b64_json(value: dict) -> str:
    return base64.b64encode(json.dumps(value, separators=(",", ":")).encode()).decode()


def column(
    name: str,
    source: str,
    data_type: str,
    *,
    hidden: bool = False,
    description: str | None = None,
) -> dict:
    result = {"name": name, "dataType": data_type, "sourceColumn": source, "summarizeBy": "none"}
    if hidden:
        result["isHidden"] = True
    if description:
        result["description"] = description
    return result


def table(
    name: str,
    columns: list[dict],
    measures: list[dict] | None = None,
    *,
    description: str | None = None,
) -> dict:
    result = {
        "name": name,
        "columns": columns,
        "partitions": [{"name": name, "mode": "directLake", "source": {
            "type": "entity", "entityName": name, "expressionSource": "DatabaseQuery",
        }}],
    }
    if description:
        result["description"] = description
    if measures:
        result["measures"] = measures
    return result


def build_model(workspace_id: str, lakehouse_id: str) -> dict:
    measures = [
        {"name": "Open Title Orders", "expression": "CALCULATE(COUNTROWS('title_order'), 'title_order'[OrderStatus] IN {\"Open\",\"Search\",\"CommitmentIssued\"})", "formatString": "#,0", "description": "Count of title orders not completed: Open, Search, or CommitmentIssued."},
        {"name": "At-Risk Orders", "expression": "CALCULATE(COUNTROWS('title_order'), 'title_order'[IsAtRisk] = TRUE())", "formatString": "#,0", "description": "Count of all title orders flagged at risk in the deterministic snapshot."},
        {"name": "Open High or Critical Orders", "expression": "CALCULATE(COUNTROWS('title_order'), 'title_order'[OrderStatus] = \"Open\", 'title_order'[RiskBand] IN {\"High\",\"Critical\"})", "formatString": "#,0", "description": "Count of Open-status title orders in the High or Critical risk bands."},
        {"name": "Open Critical Orders", "expression": "CALCULATE(COUNTROWS('title_order'), 'title_order'[OrderStatus] = \"Open\", 'title_order'[RiskBand] = \"Critical\")", "formatString": "#,0", "description": "Count of Open-status title orders in the Critical risk band."},
        {"name": "Average Days Open", "expression": "AVERAGE('title_order'[DaysOpen])", "formatString": "0.0", "description": "Average DaysOpen for the current filter context."},
        {"name": "Average Days Open Over 30", "expression": "CALCULATE(AVERAGE('title_order'[DaysOpen]), 'title_order'[DaysOpen] > 30)", "formatString": "0.0", "description": "Average DaysOpen for orders whose DaysOpen is greater than 30."},
        {"name": "Orders Past SLA", "expression": "CALCULATE(COUNTROWS('title_order'), 'title_order'[DaysOpen] > 30, 'title_order'[OrderStatus] <> \"Completed\")", "formatString": "#,0", "description": "Count of non-completed title orders open longer than 30 days."},
    ]
    model_tables = [
        table("title_order", [
            column("OrderID", "order_id", "string", description="Business identifier such as ORDER000123."),
            column("OfficeID", "office_id", "string", description="Identifier of the office handling the order."),
            column("OpenedDate", "opened_date", "dateTime"),
            column("TargetCloseDate", "target_close_date", "dateTime"),
            column("OrderStatus", "order_status", "string", description="Workflow state: Open, Search, CommitmentIssued, or Completed."),
            column("OrderType", "order_type", "string"),
            column("TransactionType", "transaction_type", "string"),
            column("Priority", "priority", "string"),
            column("RiskScore", "risk_score", "int64", description="Deterministic operational risk score from 0 through 100."),
            column("RiskBand", "risk_band", "string", description="Low, Medium, High, or Critical operational risk."),
            column("BlockingIssueCount", "blocking_issue_count", "int64"),
            column("DaysOpen", "days_open", "int64"),
            column("IsAtRisk", "is_at_risk", "boolean"),
        ], measures, description="One row per synthetic title order with workflow and current operational risk attributes."),
        table("order_risk_snapshot", [
            column("OrderID", "order_id", "string", hidden=True),
            column("UnresolvedRequiredClearanceLien", "unresolved_required_clearance_lien", "boolean"),
            column("OwnershipOrVestingMismatch", "ownership_or_vesting_mismatch", "boolean"),
            column("InstrumentAfterSearchEffectiveDate", "instrument_after_search_effective_date", "boolean"),
            column("ClosingWithinThreeDaysWithoutCommitment", "closing_within_three_days_without_commitment", "boolean"),
            column("PastServiceLevelTarget", "past_service_level_target", "boolean"),
            column("RepeatedSearchFailure", "repeated_search_failure", "boolean"),
            column("SnapshotDate", "snapshot_date", "dateTime"),
        ], description="One row per order containing deterministic risk-driver flags and the snapshot date."),
        table("agent_office", [
            column("OfficeID", "office_id", "string", description="Business identifier such as OFFICE006."),
            column("OfficeName", "office_name", "string"),
            column("Region", "region", "string"),
            column("ServiceTier", "service_tier", "string"),
        ], description="Title agent offices that handle orders."),
        table("property", [
            column("PropertyID", "property_id", "string", description="Business identifier such as PROP000321."),
            column("County", "county", "string"),
            column("State", "state", "string"),
            column("Municipality", "municipality", "string"),
            column("PropertyType", "property_type", "string"),
            column("CurrentVestingType", "current_vesting_type", "string"),
        ], description="One row per synthetic property, including geography and current vesting type."),
        table("rel_order_property", [
            column("OrderID", "order_id", "string", hidden=True),
            column("PropertyID", "property_id", "string", hidden=True),
        ], description="Bridge relating each title order to its property."),
        table("encumbrance", [
            column("EncumbranceID", "encumbrance_id", "string", description="Business identifier such as ENC000111."),
            column("OrderID", "order_id", "string", hidden=True),
            column("EncumbranceType", "encumbrance_type", "string"),
            column("ExceptionCategory", "exception_category", "string"),
            column("EncumbranceStatus", "encumbrance_status", "string"),
            column("RequiresClearance", "requires_clearance", "boolean"),
            column("ReleaseRecorded", "release_recorded", "boolean"),
        ], [
            {"name": "Unresolved Required-Clearance Encumbrances", "expression": "CALCULATE(COUNTROWS('encumbrance'), 'encumbrance'[EncumbranceStatus] = \"Open\", 'encumbrance'[RequiresClearance] = TRUE(), 'encumbrance'[ReleaseRecorded] = FALSE())", "formatString": "#,0", "description": "Count of open encumbrances requiring clearance with no recorded release."}
        ], description="Title issues and exceptions associated directly with orders."),
        table("commitment", [
            column("CommitmentID", "commitment_id", "string", description="Business identifier such as COMM000456."),
            column("OrderID", "order_id", "string", hidden=True),
            column("CommitmentStatus", "commitment_status", "string"),
        ], [
            {"name": "Commitments Issued", "expression": "CALCULATE(COUNTROWS('commitment'), 'commitment'[CommitmentStatus] = \"Issued\")", "formatString": "#,0"},
            {"name": "Issued Commitments with Issued Policy", "expression": "COUNTROWS(FILTER(VALUES('commitment'[CommitmentID]), CALCULATE(SELECTEDVALUE('commitment'[CommitmentStatus])) = \"Issued\" && CALCULATE(COUNTROWS('policy'), 'policy'[PolicyStatus] = \"Issued\") > 0))", "formatString": "#,0", "description": "Distinct issued commitments connected to at least one issued policy."},
        ], description="Commitments produced for title orders."),
        table("policy", [
            column("PolicyID", "policy_id", "string", description="Business identifier such as POLICY000900."),
            column("CommitmentID", "commitment_id", "string", hidden=True),
            column("PolicyType", "policy_type", "string"),
            column("PolicyStatus", "policy_status", "string"),
            column("PremiumAmountCents", "premium_amount_cents", "int64", description="Premium stored in cents."),
        ], [
            {"name": "Policies Issued", "expression": "CALCULATE(COUNTROWS('policy'), 'policy'[PolicyStatus] = \"Issued\")", "formatString": "#,0"},
            {"name": "Average Issued Policy Premium", "expression": "DIVIDE(CALCULATE(AVERAGE('policy'[PremiumAmountCents]), 'policy'[PolicyStatus] = \"Issued\"),100)", "formatString": "$#,0.00", "description": "Average premium in dollars for issued policies only."}
        ], description="Policies resulting from commitments, including type, status, and premium."),
    ]
    relationships = [
        {"name": str(uuid.uuid5(uuid.NAMESPACE_DNS, "title-order-office")), "fromTable": "title_order", "fromColumn": "OfficeID", "toTable": "agent_office", "toColumn": "OfficeID", "fromCardinality": "many", "toCardinality": "one", "crossFilteringBehavior": "oneDirection"},
        {"name": str(uuid.uuid5(uuid.NAMESPACE_DNS, "risk-snapshot-order")), "fromTable": "order_risk_snapshot", "fromColumn": "OrderID", "toTable": "title_order", "toColumn": "OrderID", "fromCardinality": "one", "toCardinality": "one", "crossFilteringBehavior": "bothDirections"},
        {"name": str(uuid.uuid5(uuid.NAMESPACE_DNS, "order-property-bridge-order")), "fromTable": "rel_order_property", "fromColumn": "OrderID", "toTable": "title_order", "toColumn": "OrderID", "fromCardinality": "many", "toCardinality": "one", "crossFilteringBehavior": "bothDirections"},
        {"name": str(uuid.uuid5(uuid.NAMESPACE_DNS, "order-property-bridge-property")), "fromTable": "rel_order_property", "fromColumn": "PropertyID", "toTable": "property", "toColumn": "PropertyID", "fromCardinality": "many", "toCardinality": "one", "crossFilteringBehavior": "bothDirections"},
        {"name": str(uuid.uuid5(uuid.NAMESPACE_DNS, "encumbrance-order")), "fromTable": "encumbrance", "fromColumn": "OrderID", "toTable": "title_order", "toColumn": "OrderID", "fromCardinality": "many", "toCardinality": "one", "crossFilteringBehavior": "oneDirection"},
        {"name": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commitment-order")), "fromTable": "commitment", "fromColumn": "OrderID", "toTable": "title_order", "toColumn": "OrderID", "fromCardinality": "many", "toCardinality": "one", "crossFilteringBehavior": "oneDirection"},
        {"name": str(uuid.uuid5(uuid.NAMESPACE_DNS, "policy-commitment")), "fromTable": "policy", "fromColumn": "CommitmentID", "toTable": "commitment", "toColumn": "CommitmentID", "fromCardinality": "many", "toCardinality": "one", "crossFilteringBehavior": "oneDirection"},
    ]
    return {
        "name": "title_iq_sm", "compatibilityLevel": 1604,
        "model": {
            "culture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "expressions": [{"name": "DatabaseQuery", "kind": "m", "expression": [
                "let",
                f"    Source = AzureStorage.DataLake(\"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}\", [HierarchicalNavigation=true])",
                "in",
                "    Source",
            ]}],
            "tables": model_tables, "relationships": relationships,
            "annotations": [{"name": "PBI_QueryOrder", "value": json.dumps([x["name"] for x in model_tables])}],
        },
    }


def main() -> None:
    cfg, state, client = load_config(), read_state(), FabricClient()
    definition = {"parts": [
        {"path": "model.bim", "payload": b64_json(build_model(state["workspace_id"], state["lakehouse_id"])), "payloadType": "InlineBase64"},
        {"path": "definition.pbism", "payload": b64_json({"version": "4.0", "settings": {}}), "payloadType": "InlineBase64"},
    ]}
    existing = client.find_item(state["workspace_id"], cfg.semantic_model_name, "SemanticModel")
    if existing:
        response = client.request("POST", f"workspaces/{state['workspace_id']}/semanticModels/{existing['id']}/updateDefinition?updateMetadata=false&format=TMSL", json={"definition": definition})
    else:
        response = client.request("POST", f"workspaces/{state['workspace_id']}/semanticModels", json={
            "displayName": cfg.semantic_model_name,
            "description": "AI-ready compact Direct Lake model for synthetic title-order KPIs and controlled Data Agent comparison.",
            "definition": definition,
        })
    if response.status_code >= 400:
        raise RuntimeError(f"Semantic model definition update failed: {response.status_code} {response.text}")
    result = client.wait_lro(response)
    item_id = existing["id"] if existing else ((result or {}).get("id") or client.find_item(state["workspace_id"], cfg.semantic_model_name, "SemanticModel")["id"])
    write_state({"semantic_model_id": item_id})
    print(json.dumps({"semantic_model_id": item_id, "status": "created_or_updated"}, indent=2))


if __name__ == "__main__":
    main()
