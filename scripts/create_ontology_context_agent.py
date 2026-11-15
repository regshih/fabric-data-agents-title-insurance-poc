from __future__ import annotations

import argparse
import json
from pathlib import Path

from azure.identity import AzureCliCredential
from fabric.analytics.environment.context import SetFabricDefaultContextGlobally
from fabric.analytics.environment.credentials import SetFabricAnalyticsDefaultTokenCredentialsGlobally
from fabric.dataagent.client import FabricDataAgentManagement

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, read_state, write_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an isolated Ontology-context Data Agent")
    parser.add_argument("--new-experience", action="store_true", help="Use the migrated generation-2 Ontology")
    args = parser.parse_args()
    cfg, state, client = load_config(), read_state(), FabricClient()
    workspace_id = state["workspace_id"]
    agent_name = "title_insurance_ontology_v2_context_agent" if args.new_experience else cfg.ontology_context_agent_name
    ontology_id = state["ontology_v2_id"] if args.new_experience else state["ontology_id"]
    item = client.find_item(workspace_id, agent_name, "DataAgent")
    if item is None:
        response = client.request(
            "POST",
            f"workspaces/{workspace_id}/dataAgents",
            json={
                "displayName": agent_name,
                "description": "Isolated Ontology-as-context comparison agent over synthetic title-insurance data.",
            },
        )
        client.wait_lro(response)
        item = client.find_item(workspace_id, agent_name, "DataAgent")
        if item is None:
            raise RuntimeError("Created Ontology-context agent was not discoverable")

    SetFabricAnalyticsDefaultTokenCredentialsGlobally(AzureCliCredential())
    SetFabricDefaultContextGlobally(workspace_id=workspace_id)
    agent = FabricDataAgentManagement(data_agent=item["id"], workspace=workspace_id)
    instructions = Path("agent/title_insurance_ontology_context_instructions.md").read_text(encoding="utf-8")
    agent.update_settings(
        ai_instructions=instructions,
        experimental={"enableExperimentalFeatures": True},
    )
    ontology = agent.add_staging_ontology(ontology_id, workspace_id_or_name=workspace_id)
    derived = ontology.get_datasources().get("value", [])
    agent.publish_staging(description="Ontology-as-context title-insurance comparison; synthetic data only.")
    state_prefix = "ontology_v2_context_agent" if args.new_experience else "ontology_context_agent"
    write_state({
        f"{state_prefix}_id": item["id"],
        f"{state_prefix}_published": True,
        f"{state_prefix}_runtime": "preview",
    })
    print(
        json.dumps(
            {
                "agent_id": item["id"],
                "ontology_id": ontology_id,
                "derived_sources": [source.get("displayName") for source in derived],
                "runtime": "preview",
                "published": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
