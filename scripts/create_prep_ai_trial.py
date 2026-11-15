from __future__ import annotations

import argparse
import json
from pathlib import Path

from create_or_update_comparison_agent import (
    ensure_agent,
    ensure_fabric_item_source,
    select_semantic_tables,
)
from create_semantic_model import b64_json, build_model

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, read_state, write_state


def ensure_model(client: FabricClient, workspace_id: str, lakehouse_id: str, name: str) -> dict:
    existing = client.find_item(workspace_id, name, "SemanticModel")
    if existing:
        return existing
    model = build_model(workspace_id, lakehouse_id)
    model["name"] = name
    definition = {
        "parts": [
            {"path": "model.bim", "payload": b64_json(model), "payloadType": "InlineBase64"},
            {
                "path": "definition.pbism",
                "payload": b64_json({"version": "4.0", "settings": {}}),
                "payloadType": "InlineBase64",
            },
        ]
    }
    response = client.request(
        "POST",
        f"workspaces/{workspace_id}/semanticModels",
        json={
            "displayName": name,
            "description": "Isolated Direct Lake clone for Prep for AI and Verified Answers evaluation; synthetic data.",
            "definition": definition,
        },
    )
    response.raise_for_status()
    client.wait_lro(response)
    item = client.find_item(workspace_id, name, "SemanticModel")
    if item is None:
        raise RuntimeError("Created Prep for AI semantic model was not discoverable")
    return item


def ensure_trial_agent(client: FabricClient, workspace_id: str, model_id: str, name: str) -> dict:
    item = ensure_agent(
        client,
        workspace_id,
        name,
        "Isolated semantic-model Data Agent for Prep for AI and Verified Answers comparison.",
    )
    base = f"workspaces/{workspace_id}/dataAgents/{item['id']}"
    instructions = Path("agent/title_insurance_semantic_agent_instructions.md").read_text(encoding="utf-8")
    settings = client.request(
        "PATCH",
        f"{base}/staging/settings",
        json={"aiInstructions": instructions, "experimental": {"enableExperimentalFeatures": False}},
    )
    settings.raise_for_status()
    source = ensure_fabric_item_source(client, base, workspace_id, model_id)
    selection = select_semantic_tables(client, base, source["id"])
    published = client.request(
        "POST",
        f"{base}/staging/publish",
        json={"publishedDescription": "Prep for AI comparison agent; synthetic title-insurance data only."},
    )
    published.raise_for_status()
    client.wait_lro(published)
    print(json.dumps({"agent_id": item["id"], "model_id": model_id, **selection}, indent=2))
    return item


def main() -> None:
    parser = argparse.ArgumentParser(description="Create isolated Prep for AI comparison artifacts")
    parser.add_argument("--stage", choices=["model", "agent"], required=True)
    args = parser.parse_args()
    cfg, state, client = load_config(), read_state(), FabricClient()
    workspace_id = state["workspace_id"]
    if args.stage == "model":
        name = f"{cfg.semantic_model_name}_prep_ai_trial"
        item = ensure_model(client, workspace_id, state["lakehouse_id"], name)
        write_state({"prep_ai_semantic_model_id": item["id"]})
        print(json.dumps({"model_id": item["id"], "name": name}, indent=2))
        print(
            "Refresh/frame this Direct Lake model in Power BI and configure Prep for AI "
            "before running --stage agent. Verified Answers require a report visual in "
            "the Power BI authoring UI."
        )
    else:
        model_id = state.get("prep_ai_semantic_model_id")
        if not model_id:
            raise RuntimeError("Create the Prep for AI model first")
        name = f"{cfg.semantic_data_agent_name}_prep_ai_trial"
        item = ensure_trial_agent(client, workspace_id, model_id, name)
        write_state({
            "prep_ai_data_agent_id": item["id"],
            "prep_ai_agent_published": True,
            "prep_ai_agent_runtime": "standard",
        })
        print(json.dumps({"agent_id": item["id"], "name": name, "runtime": "standard"}, indent=2))


if __name__ == "__main__":
    main()
