from __future__ import annotations

import argparse
import base64
import json
import time
import uuid
from pathlib import Path

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, read_state, write_state


def encode(value: dict) -> str:
    return base64.b64encode(json.dumps(value, separators=(",", ":")).encode()).decode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    cfg, state, client = load_config(), read_state(), FabricClient()
    notebooks = state["notebook_ids"]
    pipeline_text = Path("pipelines/pl_title_iq_build_and_validate.json").read_text(encoding="utf-8")
    pipeline_text = pipeline_text.replace("__WORKSPACE_ID__", state["workspace_id"])
    pipeline_text = pipeline_text.replace("__BUILD_NOTEBOOK_ID__", notebooks["nb_02_build_curated_tables"])
    pipeline_text = pipeline_text.replace("__VALIDATE_NOTEBOOK_ID__", notebooks["nb_03_validate_data_quality"])
    pipeline = json.loads(pipeline_text)
    platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "DataPipeline", "displayName": cfg.pipeline_name, "description": "Builds and validates managed synthetic title-insurance tables."},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_DNS, cfg.pipeline_name))},
    }
    definition = {"parts": [
        {"path": "pipeline-content.json", "payload": encode(pipeline), "payloadType": "InlineBase64"},
        {"path": ".platform", "payload": encode(platform), "payloadType": "InlineBase64"},
    ]}
    existing = client.find_item(state["workspace_id"], cfg.pipeline_name, "DataPipeline")
    if existing:
        response = client.request("POST", f"workspaces/{state['workspace_id']}/items/{existing['id']}/updateDefinition", json={"definition": definition})
    else:
        response = client.request("POST", f"workspaces/{state['workspace_id']}/items", json={"displayName": cfg.pipeline_name, "type": "DataPipeline", "definition": definition})
    result = client.wait_lro(response)
    item_id = existing["id"] if existing else ((result or {}).get("id") or client.find_item(state["workspace_id"], cfg.pipeline_name, "DataPipeline")["id"])
    write_state({"pipeline_id": item_id})
    print(json.dumps({"pipeline_id": item_id}, indent=2))
    if args.run:
        run = client.request("POST", f"workspaces/{state['workspace_id']}/items/{item_id}/jobs/instances?jobType=Pipeline")
        run.raise_for_status()
        while True:
            time.sleep(10)
            status = client.request("GET", run.headers["Location"])
            status.raise_for_status()
            body = status.json()
            if body["status"] in {"Completed", "Failed", "Cancelled", "Deduped"}:
                print(json.dumps(body, indent=2))
                if body["status"] != "Completed":
                    raise RuntimeError(body)
                break


if __name__ == "__main__":
    main()

