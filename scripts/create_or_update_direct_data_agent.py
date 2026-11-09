from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import quote

from title_iq.fabric_api import FabricClient, read_state, write_state

AGENT_NAME = "title_insurance_direct_agent"
SELECTED_TABLES = {
    "property",
    "party",
    "agent_office",
    "title_order",
    "recorded_instrument",
    "encumbrance",
    "commitment",
    "policy",
    "rel_order_property",
    "rel_order_party",
    "rel_property_instrument",
    "rel_order_encumbrance",
    "rel_order_commitment",
    "rel_commitment_policy",
    "rel_order_office",
    "rel_instrument_encumbrance",
    "order_risk_snapshot",
    "daily_title_operations",
    "property_title_summary",
}


def values(response) -> list[dict]:
    response.raise_for_status()
    return response.json().get("value", [])


def wait_for_datasource(client: FabricClient, base: str, timeout_seconds: int = 600) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        sources = values(client.request("GET", f"{base}/staging/datasources"))
        if sources:
            return sources[0]
        time.sleep(5)
    raise TimeoutError("Lakehouse datasource did not become discoverable")


def list_elements(client: FabricClient, base: str, source_id: str, root_id: str | None = None) -> list[dict]:
    suffix = "" if root_id is None else f"?rootId={quote(root_id, safe='')}"
    response = client.request("GET", f"{base}/staging/datasources/{source_id}/elements{suffix}")
    return values(response)


def discover_tables(client: FabricClient, base: str, source_id: str, roots: list[dict]) -> dict[str, dict]:
    tables: dict[str, dict] = {}
    queue = list(roots)
    visited: set[str] = set()
    while queue:
        element = queue.pop(0)
        element_id = element["id"]
        if element_id in visited:
            continue
        visited.add(element_id)
        if element.get("type") == "Table":
            tables[element["displayName"]] = element
        elif element.get("hasSubElements"):
            queue.extend(list_elements(client, base, source_id, element_id))
    return tables


def main() -> None:
    state = read_state()
    workspace_id = state["workspace_id"]
    lakehouse_id = state["lakehouse_id"]
    client = FabricClient()

    item = client.find_item(workspace_id, AGENT_NAME, "DataAgent")
    if not item:
        response = client.request(
            "POST",
            f"workspaces/{workspace_id}/dataAgents",
            json={
                "displayName": AGENT_NAME,
                "description": "Synthetic title-insurance Data Agent backed directly by Lakehouse tables; no Ontology source.",
            },
        )
        client.wait_lro(response)
        item = client.find_item(workspace_id, AGENT_NAME, "DataAgent")
    if not item:
        raise RuntimeError("Data Agent creation completed but the item was not discoverable")

    agent_id = item["id"]
    base = f"workspaces/{workspace_id}/dataAgents/{agent_id}"
    instructions = Path("agent/title_insurance_direct_agent_instructions.md").read_text(encoding="utf-8")
    settings = client.request("PATCH", f"{base}/staging/settings", json={"aiInstructions": instructions})
    settings.raise_for_status()

    sources = values(client.request("GET", f"{base}/staging/datasources"))
    if not sources:
        response = client.request(
            "POST",
            f"{base}/staging/datasources",
            json={
                "type": "LakehouseTables",
                "lakehouseReference": {
                    "referenceType": "ById",
                    "itemId": lakehouse_id,
                    "workspaceId": workspace_id,
                },
            },
        )
        if response.status_code == 202:
            client.wait_lro(response, timeout_seconds=900)
        elif response.status_code not in {200, 201, 409}:
            response.raise_for_status()
        source = wait_for_datasource(client, base)
    else:
        source = sources[0]

    source_id = source["id"]
    metadata = client.request(
        "PATCH",
        f"{base}/staging/datasources/{source_id}",
        json={
            "description": "Managed Delta tables for synthetic title orders, properties, parties, recorded instruments, encumbrances, commitments, policies, offices, relationships, and deterministic risk snapshots.",
            "instructions": "Use relationship tables for joins and order_risk_snapshot for risk metrics. Never estimate counts or invent missing relationships.",
        },
    )
    metadata.raise_for_status()

    deadline = time.time() + 900
    roots: list[dict] = []
    while time.time() < deadline:
        roots = list_elements(client, base, source_id)
        if roots and all(element.get("state") != "SchemaUnavailable" for element in roots):
            break
        time.sleep(10)
    available = discover_tables(client, base, source_id, roots)
    missing = sorted(SELECTED_TABLES - available.keys())
    if missing:
        raise RuntimeError(f"Expected Lakehouse tables were not visible to Data Agent: {missing}")
    for name, table in available.items():
        should_select = name in SELECTED_TABLES
        if table.get("isSelected") != should_select:
            response = client.request(
                "PATCH",
                f"{base}/staging/datasources/{source_id}/elements?id={quote(table['id'], safe='')}",
                json={"isSelected": should_select},
            )
            response.raise_for_status()

    publish = client.request(
        "POST",
        f"{base}/staging/publish",
        json={
            "publishedDescription": "Answers operational questions over synthetic title-insurance Lakehouse tables without using an Ontology. Risk is not legal advice."
        },
    )
    publish.raise_for_status()
    write_state({"direct_data_agent_id": agent_id, "direct_agent_published": True})
    print(json.dumps({"data_agent_id": agent_id, "datasource_id": source_id, "selected_tables": len(SELECTED_TABLES), "published": True}, indent=2))


if __name__ == "__main__":
    main()
