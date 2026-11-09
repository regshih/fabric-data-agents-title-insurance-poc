from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PocConfig:
    subscription_id: str
    tenant_id: str
    resource_group: str
    region: str
    capacity_name: str
    capacity_sku: str
    maximum_test_sku: str
    workspace_name: str
    domain_name: str
    lakehouse_name: str
    semantic_model_name: str
    ontology_name: str
    data_agent_name: str
    semantic_data_agent_name: str
    hybrid_data_agent_name: str
    pipeline_name: str
    seed: int
    as_of_date: str
    tier: str


def load_config(path: str | Path = "config/poc.yaml") -> PocConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    azure, fabric, data = raw["azure"], raw["fabric"], raw["data"]
    env = os.environ
    return PocConfig(
        subscription_id=env.get("AZURE_SUBSCRIPTION_ID", azure["subscription_id"]),
        tenant_id=env.get("AZURE_TENANT_ID", azure["tenant_id"]),
        resource_group=env.get("AZURE_RESOURCE_GROUP", azure["resource_group"]),
        region=env.get("AZURE_REGION", azure["region"]),
        capacity_name=env.get("FABRIC_CAPACITY_NAME", fabric["capacity_name"]),
        capacity_sku=env.get("FABRIC_CAPACITY_SKU", fabric["starting_sku"]),
        maximum_test_sku=fabric["maximum_test_sku"],
        workspace_name=env.get("FABRIC_WORKSPACE_NAME", fabric["workspace_name"]),
        domain_name=fabric["domain_name"],
        lakehouse_name=env.get("FABRIC_LAKEHOUSE_NAME", fabric["lakehouse_name"]),
        semantic_model_name=fabric["semantic_model_name"],
        ontology_name=env.get("FABRIC_ONTOLOGY_NAME", fabric["ontology_name"]),
        data_agent_name=env.get("FABRIC_DATA_AGENT_NAME", fabric["data_agent_name"]),
        semantic_data_agent_name=env.get(
            "FABRIC_SEMANTIC_DATA_AGENT_NAME", fabric["semantic_data_agent_name"]
        ),
        hybrid_data_agent_name=env.get(
            "FABRIC_HYBRID_DATA_AGENT_NAME", fabric["hybrid_data_agent_name"]
        ),
        pipeline_name=fabric["pipeline_name"],
        seed=int(env.get("SYNTHETIC_SEED", data["seed"])),
        as_of_date=env.get("AS_OF_DATE", str(data["as_of_date"])),
        tier=env.get("DATASET_TIER", data["tier"]),
    )
