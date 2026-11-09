from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import quote

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, read_state, write_state

SEMANTIC_TABLES = {
    "title_order",
    "order_risk_snapshot",
    "agent_office",
    "property",
    "encumbrance",
    "commitment",
    "policy",
}


def values(response) -> list[dict]:
    response.raise_for_status()
    return response.json().get("value", [])


def ensure_agent(client: FabricClient, workspace_id: str, name: str, description: str) -> dict:
    item = client.find_item(workspace_id, name, "DataAgent")
    if item:
        return item
    response = client.request(
        "POST",
        f"workspaces/{workspace_id}/dataAgents",
        json={"displayName": name, "description": description},
    )
    client.wait_lro(response)
    item = client.find_item(workspace_id, name, "DataAgent")
    if not item:
        raise RuntimeError(f"Data Agent {name!r} was created but is not discoverable")
    return item


def find_source(sources: list[dict], item_id: str) -> dict | None:
    return next(
        (
            source
            for source in sources
            if source.get("itemReference", {}).get("itemId") == item_id
            or source.get("lakehouseReference", {}).get("itemId") == item_id
        ),
        None,
    )


def ensure_fabric_item_source(
    client: FabricClient,
    base: str,
    workspace_id: str,
    item_id: str,
    *,
    timeout_seconds: int = 900,
) -> dict:
    sources = values(client.request("GET", f"{base}/staging/datasources"))
    source = find_source(sources, item_id)
    if source:
        return source

    response = client.request(
        "POST",
        f"{base}/staging/datasources",
        json={
            "type": "FabricItem",
            "itemReference": {
                "referenceType": "ById",
                "itemId": item_id,
                "workspaceId": workspace_id,
            },
        },
    )
    if response.status_code == 202:
        client.wait_lro(response, timeout_seconds=timeout_seconds)
    elif response.status_code not in {200, 201, 409}:
        response.raise_for_status()

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        sources = values(client.request("GET", f"{base}/staging/datasources"))
        source = find_source(sources, item_id)
        if source:
            return source
        time.sleep(5)
    raise TimeoutError(f"Data source {item_id} did not become discoverable")


def list_elements(
    client: FabricClient,
    base: str,
    source_id: str,
    root_id: str | None = None,
) -> list[dict]:
    suffix = "" if root_id is None else f"?rootId={quote(root_id, safe='')}"
    return values(client.request("GET", f"{base}/staging/datasources/{source_id}/elements{suffix}"))


def discover_tables(client: FabricClient, base: str, source_id: str) -> dict[str, dict]:
    queue = list_elements(client, base, source_id)
    tables: dict[str, dict] = {}
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


def select_semantic_tables(client: FabricClient, base: str, source_id: str) -> dict[str, object]:
    deadline = time.time() + 900
    available: dict[str, dict] = {}
    while time.time() < deadline:
        available = discover_tables(client, base, source_id)
        if SEMANTIC_TABLES.issubset(available):
            break
        time.sleep(10)
    missing = sorted(SEMANTIC_TABLES - available.keys())
    if missing:
        raise RuntimeError(f"Semantic-model tables were not visible to Data Agent: {missing}")

    for name, table in available.items():
        should_select = name in SEMANTIC_TABLES
        if table.get("isSelected") != should_select:
            response = client.request(
                "PATCH",
                f"{base}/staging/datasources/{source_id}/elements?id={quote(table['id'], safe='')}",
                json={"isSelected": should_select},
            )
            response.raise_for_status()
    return {"selected": sorted(SEMANTIC_TABLES), "available": sorted(available)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create semantic-only or native hybrid comparison agent")
    parser.add_argument("--agent", choices=["semantic", "hybrid"], required=True)
    parser.add_argument("--runtime", choices=["standard", "preview"], default="standard")
    args = parser.parse_args()

    cfg, state, client = load_config(), read_state(), FabricClient()
    workspace_id = state["workspace_id"]
    if args.agent == "semantic":
        name = cfg.semantic_data_agent_name
        instructions_path = Path("agent/title_insurance_semantic_agent_instructions.md")
        description = "Semantic-model-only title-insurance KPI Data Agent for controlled evaluation."
        state_id_key = "semantic_data_agent_id"
        state_runtime_key = "semantic_agent_runtime"
        published_key = "semantic_agent_published"
    else:
        name = cfg.hybrid_data_agent_name
        instructions_path = Path("agent/title_insurance_hybrid_agent_instructions.md")
        description = "Native multi-source title-insurance Data Agent using semantic-model KPIs and Ontology relationships."
        state_id_key = "hybrid_data_agent_id"
        state_runtime_key = "hybrid_agent_runtime"
        published_key = "hybrid_agent_published"

    item = ensure_agent(client, workspace_id, name, description)
    agent_id = item["id"]
    base = f"workspaces/{workspace_id}/dataAgents/{agent_id}"
    instructions = instructions_path.read_text(encoding="utf-8")
    settings = client.request(
        "PATCH",
        f"{base}/staging/settings",
        json={
            "aiInstructions": instructions,
            "experimental": {"enableExperimentalFeatures": args.runtime == "preview"},
        },
    )
    settings.raise_for_status()

    semantic_source = ensure_fabric_item_source(
        client,
        base,
        workspace_id,
        state["semantic_model_id"],
    )
    schema = select_semantic_tables(client, base, semantic_source["id"])
    source_results = [{"name": "title_iq_sm", "id": semantic_source["id"], **schema}]

    if args.agent == "hybrid":
        ontology_source = ensure_fabric_item_source(
            client,
            base,
            workspace_id,
            state["ontology_id"],
        )
        metadata = client.request(
            "PATCH",
            f"{base}/staging/datasources/{ontology_source['id']}",
            json={
                "description": (
                    "Use for entity relationship traversal among title orders, properties, parties, "
                    "instruments, encumbrances, commitments, policies, and offices."
                )
            },
        )
        metadata.raise_for_status()
        source_results.append({"name": "title_insurance_ontology", "id": ontology_source["id"]})

    publish = client.request(
        "POST",
        f"{base}/staging/publish",
        json={
            "publishedDescription": (
                f"{args.agent.capitalize()} title-insurance Data Agent comparison; "
                "synthetic data and operational risk only."
            )
        },
    )
    publish.raise_for_status()
    write_state(
        {
            state_id_key: agent_id,
            state_runtime_key: args.runtime,
            published_key: True,
        }
    )
    print(
        json.dumps(
            {
                "agent": args.agent,
                "data_agent_id": agent_id,
                "runtime": args.runtime,
                "sources": source_results,
                "published": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
