from __future__ import annotations

import argparse
import json
import time

from title_iq.fabric_api import FabricClient, read_state, write_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    state = read_state()
    client = FabricClient()
    graph_id = state.get("graph_item_id")
    if not graph_id:
        graph = next((x for x in client.list_all(f"workspaces/{state['workspace_id']}/items") if x["type"] == "GraphModel"), None)
        if not graph:
            raise RuntimeError("GraphModel child item is not present; ontology may still be materializing")
        graph_id = graph["id"]
    started = time.time()
    response = client.request("POST", f"workspaces/{state['workspace_id']}/items/{graph_id}/jobs/RefreshGraph/instances")
    response.raise_for_status()
    location = response.headers["Location"]
    while time.time() - started < args.timeout:
        time.sleep(10)
        status = client.request("GET", location)
        status.raise_for_status()
        body = status.json()
        if body["status"] in {"Completed", "Failed", "Cancelled", "Deduped"}:
            if body["status"] not in {"Completed", "Deduped"}:
                raise RuntimeError(json.dumps(body))
            write_state({"graph_item_id": graph_id, "graph_refresh_seconds": round(time.time() - started, 2), "graph_refresh_status": body["status"]})
            print(json.dumps(body, indent=2))
            return
    raise TimeoutError("graph refresh timed out")


if __name__ == "__main__":
    main()

