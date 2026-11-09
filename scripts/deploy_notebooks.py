from __future__ import annotations

import argparse
import base64
import json
import time
import uuid
from pathlib import Path

from title_iq.fabric_api import FabricClient, read_state, write_state


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def notebook_definition(name: str, content: str) -> dict:
    platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Notebook", "displayName": name, "description": "Synthetic title-insurance POC notebook."},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fabric-iq-title-insurance-poc/{name}"))},
    }
    return {"parts": [
        {"path": "notebook-content.py", "payload": b64(content), "payloadType": "InlineBase64"},
        {"path": ".platform", "payload": b64(json.dumps(platform)), "payloadType": "InlineBase64"},
    ]}


def run_job(client: FabricClient, workspace_id: str, item_id: str) -> dict:
    response = client.request("POST", f"workspaces/{workspace_id}/items/{item_id}/jobs/instances?jobType=RunNotebook")
    response.raise_for_status()
    location = response.headers["Location"]
    while True:
        time.sleep(10)
        status = client.request("GET", location)
        status.raise_for_status()
        body = status.json()
        if body["status"] in {"Completed", "Failed", "Cancelled", "Deduped"}:
            if body["status"] != "Completed":
                raise RuntimeError(json.dumps(body))
            return body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    state = read_state()
    client = FabricClient()
    ids = {}
    for path in sorted(Path("notebooks").glob("nb_*.py")):
        name = path.stem
        content = path.read_text(encoding="utf-8").replace("__WORKSPACE_ID__", state["workspace_id"]).replace("__LAKEHOUSE_ID__", state["lakehouse_id"])
        definition = notebook_definition(name, content)
        existing = client.find_item(state["workspace_id"], name, "Notebook")
        if existing:
            item_id = existing["id"]
            response = client.request("POST", f"workspaces/{state['workspace_id']}/items/{item_id}/updateDefinition", json={"definition": definition})
        else:
            response = client.request("POST", f"workspaces/{state['workspace_id']}/items", json={"displayName": name, "type": "Notebook", "definition": definition})
        result = client.wait_lro(response)
        item_id = item_id if existing else ((result or {}).get("id") or client.find_item(state["workspace_id"], name, "Notebook")["id"])
        ids[name] = item_id
        print(f"deployed {name}: {item_id}")
        if args.run:
            print(json.dumps(run_job(client, state["workspace_id"], item_id), indent=2))
    write_state({"notebook_ids": ids})


if __name__ == "__main__":
    main()

