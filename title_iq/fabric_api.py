from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from azure.identity import AzureCliCredential

FABRIC_API = "https://api.fabric.microsoft.com/v1"


class FabricClient:
    def __init__(self) -> None:
        token = AzureCliCredential().get_token("https://api.fabric.microsoft.com/.default").token
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = path if path.startswith("http") else f"{FABRIC_API}/{path.lstrip('/')}"
        for attempt in range(6):
            response = self.session.request(method, url, timeout=120, **kwargs)
            if response.status_code != 429 and response.status_code < 500:
                return response
            time.sleep(int(response.headers.get("Retry-After", min(2 ** attempt, 30))))
        return response

    def wait_lro(self, response: requests.Response, timeout_seconds: int = 1800) -> dict[str, Any] | None:
        if response.status_code != 202:
            response.raise_for_status()
            return response.json() if response.content else None
        operation_id = response.headers.get("x-ms-operation-id")
        operation_url = f"{FABRIC_API}/operations/{operation_id}" if operation_id else response.headers["Location"]
        deadline = time.time() + timeout_seconds
        wait_seconds = int(response.headers.get("Retry-After", 5))
        while time.time() < deadline:
            time.sleep(wait_seconds)
            status = self.request("GET", operation_url)
            status.raise_for_status()
            body = status.json()
            state = body.get("status")
            if state == "Succeeded":
                result = self.request("GET", f"{operation_url}/result")
                return result.json() if result.status_code == 200 and result.content else body
            if state in {"Failed", "Cancelled"}:
                raise RuntimeError(f"Fabric operation {state}: {json.dumps(body)}")
            wait_seconds = int(status.headers.get("Retry-After", wait_seconds))
        raise TimeoutError(f"Fabric operation did not complete in {timeout_seconds}s")

    def list_all(self, path: str) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        next_path: str | None = path
        while next_path:
            response = self.request("GET", next_path)
            response.raise_for_status()
            body = response.json()
            values.extend(body.get("value", []))
            next_path = body.get("continuationUri")
        return values

    def find_workspace(self, display_name: str) -> dict[str, Any] | None:
        return next((x for x in self.list_all("workspaces") if x["displayName"] == display_name), None)

    def find_item(self, workspace_id: str, display_name: str, item_type: str | None = None) -> dict[str, Any] | None:
        items = self.list_all(f"workspaces/{workspace_id}/items")
        return next((x for x in items if x["displayName"] == display_name and (not item_type or x["type"] == item_type)), None)

    def ensure_item(self, workspace_id: str, display_name: str, item_type: str, description: str) -> dict[str, Any]:
        existing = self.find_item(workspace_id, display_name, item_type)
        if existing:
            if existing.get("description") != description:
                update = self.request("PATCH", f"workspaces/{workspace_id}/items/{existing['id']}", json={"description": description})
                update.raise_for_status()
            return existing
        response = self.request("POST", f"workspaces/{workspace_id}/items", json={
            "displayName": display_name, "description": description, "type": item_type,
        })
        result = self.wait_lro(response)
        if result and result.get("id"):
            return result
        created = self.find_item(workspace_id, display_name, item_type)
        if not created:
            raise RuntimeError(f"created {item_type} {display_name!r}, but it was not discoverable")
        return created


def write_state(values: dict[str, Any], path: str | Path = "local-output/environment-state.json") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    current = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    current.update(values)
    target.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")


def read_state(path: str | Path = "local-output/environment-state.json") -> dict[str, Any]:
    target = Path(path)
    return json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}

