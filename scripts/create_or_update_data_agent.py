from __future__ import annotations

import json
import time
from pathlib import Path

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, read_state, write_state


def values(response) -> list[dict]:
    response.raise_for_status()
    return response.json().get("value", [])


def main() -> None:
    cfg, state = load_config(), read_state()
    ontology_id = state.get("ontology_id")
    if not ontology_id:
        raise RuntimeError("ontology_id is absent; create the Ontology before publishing its agent")

    client = FabricClient()
    workspace_id = state["workspace_id"]
    item = client.find_item(workspace_id, cfg.data_agent_name, "DataAgent")
    if not item:
        response = client.request(
            "POST",
            f"workspaces/{workspace_id}/dataAgents",
            json={
                "displayName": cfg.data_agent_name,
                "description": "Ontology-grounded synthetic title-insurance operations agent.",
            },
        )
        client.wait_lro(response)
        item = client.find_item(workspace_id, cfg.data_agent_name, "DataAgent")
    if not item:
        raise RuntimeError("Data Agent creation completed but the item was not discoverable")

    agent_id = item["id"]
    base = f"workspaces/{workspace_id}/dataAgents/{agent_id}"
    instructions = Path("agent/title_insurance_agent_instructions.md").read_text(encoding="utf-8")
    response = client.request("PATCH", f"{base}/staging/settings", json={"aiInstructions": instructions})
    response.raise_for_status()

    sources = values(client.request("GET", f"{base}/staging/datasources"))
    source = next((entry for entry in sources if ontology_id in json.dumps(entry)), None)
    if not source:
        response = client.request(
            "POST",
            f"{base}/staging/datasources",
            json={
                "type": "FabricItem",
                "itemReference": {
                    "referenceType": "ById",
                    "itemId": ontology_id,
                    "workspaceId": workspace_id,
                },
            },
        )
        if response.status_code == 202:
            client.wait_lro(response, timeout_seconds=900)
        elif response.status_code not in {200, 201, 409}:
            response.raise_for_status()
        deadline = time.time() + 600
        while time.time() < deadline:
            sources = values(client.request("GET", f"{base}/staging/datasources"))
            source = next((entry for entry in sources if ontology_id in json.dumps(entry)), None)
            if source:
                break
            time.sleep(5)
    if not source:
        raise RuntimeError("Ontology datasource did not become discoverable")

    response = client.request(
        "PATCH",
        f"{base}/staging/datasources/{source['id']}",
        json={
            "description": "Authoritative synthetic title-insurance ontology for orders, properties, parties, instruments, encumbrances, commitments, policies, and offices."
        },
    )
    response.raise_for_status()
    publish = client.request(
        "POST",
        f"{base}/staging/publish",
        json={
            "publishedDescription": "Ontology-only synthetic title-insurance operations agent; risk is not legal advice."
        },
    )
    publish.raise_for_status()
    write_state({"data_agent_id": agent_id, "agent_runtime": "standard", "agent_published": True})
    print(json.dumps({"data_agent_id": agent_id, "ontology_id": ontology_id, "runtime": "standard", "published": True}, indent=2))


if __name__ == "__main__":
    main()
