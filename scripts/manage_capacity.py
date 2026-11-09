from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

import requests
from azure.identity import AzureCliCredential

from title_iq.config import load_config

API_VERSION = "2023-11-01"


def az_json(*args: str) -> dict:
    executable = shutil.which("az") or shutil.which("az.cmd")
    if not executable:
        raise RuntimeError("Azure CLI was not found on PATH")
    result = subprocess.run([executable, *args, "-o", "json"], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def arm_session() -> requests.Session:
    token = AzureCliCredential().get_token("https://management.azure.com/.default").token
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return session


def resource_url(subscription: str, group: str, name: str) -> str:
    return f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{group}/providers/Microsoft.Fabric/capacities/{name}?api-version={API_VERSION}"


def ensure_capacity() -> dict:
    cfg = load_config()
    account = az_json("account", "show")
    if account["id"] != cfg.subscription_id or account["tenantId"] != cfg.tenant_id:
        raise RuntimeError("active Azure subscription/tenant does not match config/poc.yaml")
    az_json("group", "create", "--subscription", cfg.subscription_id, "--name", cfg.resource_group, "--location", cfg.region,
            "--tags", "purpose=fabric-iq-title-insurance-poc", "data=synthetic")
    user = account["user"]["name"]
    body = {
        "location": cfg.region,
        "sku": {"name": cfg.capacity_sku, "tier": "Fabric"},
        "tags": {"purpose": "fabric-iq-title-insurance-poc", "data": "synthetic", "pauseWhenIdle": "true"},
        "properties": {"administration": {"members": [user]}},
    }
    session = arm_session()
    response = session.put(resource_url(cfg.subscription_id, cfg.resource_group, cfg.capacity_name), json=body, timeout=180)
    response.raise_for_status()
    return response.json()


def action(command: str, sku: str | None = None) -> dict:
    cfg = load_config()
    session = arm_session()
    base = resource_url(cfg.subscription_id, cfg.resource_group, cfg.capacity_name)
    if command == "status":
        response = session.get(base, timeout=60)
    elif command in {"resume", "pause"}:
        verb = "resume" if command == "resume" else "suspend"
        response = session.post(base.replace(f"?api-version={API_VERSION}", f"/{verb}?api-version={API_VERSION}"), timeout=180)
    elif command == "resize":
        allowed = ["F2", "F4", "F8", "F16", "F32", "F64"]
        if sku not in allowed or allowed.index(sku) > allowed.index(cfg.maximum_test_sku):
            raise ValueError(f"SKU must be one of {allowed} and no larger than {cfg.maximum_test_sku}")
        response = session.patch(base, json={"sku": {"name": sku, "tier": "Fabric"}}, timeout=180)
    else:
        raise ValueError(command)
    response.raise_for_status()
    return response.json() if response.content else {"status": "Accepted", "command": command}


def main() -> None:
    parser = argparse.ArgumentParser(description="Idempotently manage the dedicated POC Fabric capacity")
    parser.add_argument("command", choices=["ensure", "status", "resume", "pause", "resize"])
    parser.add_argument("--sku")
    args = parser.parse_args()
    result = ensure_capacity() if args.command == "ensure" else action(args.command, args.sku)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    sys.exit(main())
