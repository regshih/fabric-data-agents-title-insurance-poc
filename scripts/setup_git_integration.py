from __future__ import annotations

import argparse
import os
import time

from title_iq.fabric_api import FabricClient, read_state

CONNECTION_NAME = "fabric-iq-title-insurance-poc-git"


def wait(client: FabricClient, response) -> None:
    if response.status_code != 202:
        response.raise_for_status()
        return
    client.wait_lro(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", default="main")
    parser.add_argument("--directory", default="fabric_git")
    args = parser.parse_args()
    pat = os.environ.get("GITHUB_PAT")
    if not pat:
        raise RuntimeError("set GITHUB_PAT in the process environment; never store it in .env or the repository")
    state, client = read_state(), FabricClient()
    connections = client.list_all("connections")
    connection = next((x for x in connections if x["displayName"] == CONNECTION_NAME), None)
    if not connection:
        response = client.request("POST", "connections", json={
            "connectivityType": "ShareableCloud", "displayName": CONNECTION_NAME,
            "connectionDetails": {"type": "GitHubSourceControl", "creationMethod": "GitHubSourceControl.Contents",
                                  "parameters": [{"dataType": "Text", "name": "url", "value": "https://github.com/regshih/fabric-data-agents-title-insurance-poc"}]},
            "credentialDetails": {"credentials": {"credentialType": "Key", "key": pat}},
        })
        response.raise_for_status()
        connection = response.json()
    current = client.request("GET", f"workspaces/{state['workspace_id']}/git/connection")
    current.raise_for_status()
    if current.json()["gitConnectionState"] == "NotConnected":
        response = client.request("POST", f"workspaces/{state['workspace_id']}/git/connect", json={
            "gitProviderDetails": {"gitProviderType": "GitHub", "ownerName": "regshih", "repositoryName": "fabric-data-agents-title-insurance-poc",
                                   "branchName": args.branch, "directoryName": args.directory},
            "myGitCredentials": {"source": "ConfiguredConnection", "connectionId": connection["id"]},
        })
        response.raise_for_status()
    credential = client.request("PATCH", f"workspaces/{state['workspace_id']}/git/myGitCredentials",
                                json={"source": "ConfiguredConnection", "connectionId": connection["id"]})
    credential.raise_for_status()
    time.sleep(2)
    current = client.request("GET", f"workspaces/{state['workspace_id']}/git/connection").json()
    if current["gitConnectionState"] != "ConnectedAndInitialized":
        response = client.request("POST", f"workspaces/{state['workspace_id']}/git/initializeConnection", json={})
        response.raise_for_status()
        initialization = response.json()
        if initialization["requiredAction"] == "CommitToGit":
            commit = client.request("POST", f"workspaces/{state['workspace_id']}/git/commitToGit", json={
                "mode": "All", "workspaceHead": initialization["workspaceHead"],
                "comment": "Sync supported Fabric items for title-insurance POC",
            })
            wait(client, commit)
        elif initialization["requiredAction"] == "UpdateFromGit":
            update = client.request("POST", f"workspaces/{state['workspace_id']}/git/updateFromGit", json={
                "workspaceHead": initialization["workspaceHead"], "remoteCommitHash": initialization["remoteCommitHash"]
            })
            wait(client, update)
    print(client.request("GET", f"workspaces/{state['workspace_id']}/git/connection").json()["gitConnectionState"])


if __name__ == "__main__":
    main()

