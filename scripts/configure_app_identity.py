from __future__ import annotations

import argparse
import json

from title_iq.fabric_api import FabricClient, read_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Grant the showcase application least-privilege Fabric access")
    parser.add_argument("--service-principal-id", required=True, help="Entra service-principal object ID")
    args = parser.parse_args()

    state = read_state()
    client = FabricClient()
    workspace_id = state["workspace_id"]
    assignments = client.list_all(f"workspaces/{workspace_id}/roleAssignments")
    existing = next((x for x in assignments if x["principal"]["id"] == args.service_principal_id), None)
    if existing:
        result = {"action": "unchanged", "role": existing["role"], "assignmentId": existing["id"]}
    else:
        response = client.request(
            "POST",
            f"workspaces/{workspace_id}/roleAssignments",
            json={
                "principal": {"id": args.service_principal_id, "type": "ServicePrincipal"},
                "role": "Contributor",
            },
        )
        response.raise_for_status()
        created = response.json()
        result = {"action": "created", "role": created["role"], "assignmentId": created["id"]}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
