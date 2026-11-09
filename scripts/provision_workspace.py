from __future__ import annotations

import json

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, write_state


def main() -> None:
    cfg = load_config()
    client = FabricClient()
    capacity = next((x for x in client.list_all("capacities") if x["displayName"] == cfg.capacity_name), None)
    if not capacity:
        raise RuntimeError(f"capacity {cfg.capacity_name!r} is not active/visible; run manage_capacity.py ensure and resume")
    workspace = client.find_workspace(cfg.workspace_name)
    if workspace:
        if workspace.get("capacityId") != capacity["id"]:
            response = client.request("POST", f"workspaces/{workspace['id']}/assignToCapacity", json={"capacityId": capacity["id"]})
            response.raise_for_status()
    else:
        response = client.request("POST", "workspaces", json={
            "displayName": cfg.workspace_name,
            "description": "Private POC for governed title-insurance intelligence; all records are synthetic.",
            "capacityId": capacity["id"],
        })
        response.raise_for_status()
        workspace = response.json()
    lakehouse = client.ensure_item(
        workspace["id"], cfg.lakehouse_name, "Lakehouse",
        "Authoritative curated managed Delta tables for the synthetic title-insurance Fabric IQ POC.",
    )
    state = {
        "capacity_id": capacity["id"], "capacity_name": cfg.capacity_name, "capacity_sku": capacity.get("sku"),
        "workspace_id": workspace["id"], "workspace_name": cfg.workspace_name,
        "lakehouse_id": lakehouse["id"], "lakehouse_name": cfg.lakehouse_name,
    }
    write_state(state)
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()

