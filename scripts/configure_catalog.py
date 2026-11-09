from __future__ import annotations

import argparse
import json

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, read_state, write_state

DESCRIPTIONS = {
    "title_iq_lh": "Authoritative managed OneLake Delta tables for a wholly synthetic title-insurance operations POC.",
    "title_iq_sm": "Compact Direct Lake semantic model with governed title-order, risk, exception, commitment, and policy KPIs.",
    "title_insurance_ontology": "Preview ontology defining eight title-insurance business entities and their governed relationships.",
    "title_insurance_iq_agent": "Focused published data agent grounded only in the synthetic title-insurance ontology.",
    "title_insurance_direct_agent": "Comparison data agent grounded directly in selected synthetic Lakehouse tables without an Ontology source.",
    "pl_title_iq_build_and_validate": "Orchestrates curated-table materialization and data-quality validation for synthetic data.",
    "nb_02_build_curated_tables": "Materializes uploaded fictional title-insurance parquet as managed Delta tables.",
    "nb_03_validate_data_quality": "Checks entity keys, relationship endpoints, and risk score bounds before ontology binding.",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--try-domain", action="store_true")
    args = parser.parse_args()
    cfg, state, client = load_config(), read_state(), FabricClient()
    items = client.list_all(f"workspaces/{state['workspace_id']}/items")
    updated = []
    for item in items:
        description = DESCRIPTIONS.get(item["displayName"])
        if description and item.get("description") != description:
            response = client.request("PATCH", f"workspaces/{state['workspace_id']}/items/{item['id']}", json={"description": description})
            response.raise_for_status()
            updated.append(item["displayName"])
    domain_status = "not-requested"
    if args.try_domain:
        response = client.request("GET", "admin/domains?preview=false")
        if response.status_code == 403:
            domain_status = "manual-required: Tenant.ReadWrite.All/Fabric admin"
        else:
            response.raise_for_status()
            domains = response.json().get("domains", response.json().get("value", []))
            domain = next((d for d in domains if d["displayName"] == cfg.domain_name), None)
            if not domain:
                create = client.request("POST", "admin/domains?preview=false", json={"displayName": cfg.domain_name, "description": "Governed title-insurance analytics and operational intelligence."})
                create.raise_for_status()
                domain = create.json()
            assign = client.request("POST", f"admin/domains/{domain['id']}/assignWorkspaces", json={"workspacesIds": [state["workspace_id"]]})
            assign.raise_for_status()
            domain_status = f"assigned:{domain['id']}"
    search = client.request("POST", "catalog/search", json={"search": "title insurance", "pageSize": 50})
    catalog_status = "verified" if search.status_code == 200 else f"unverified:{search.status_code}"
    write_state({"catalog_status": catalog_status, "domain_status": domain_status})
    print(json.dumps({"updated_descriptions": updated, "catalog_status": catalog_status, "domain_status": domain_status}, indent=2))


if __name__ == "__main__":
    main()
