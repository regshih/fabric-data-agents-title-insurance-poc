from __future__ import annotations

import base64
import hashlib
import json
import uuid
from pathlib import Path

from title_iq.config import load_config
from title_iq.fabric_api import FabricClient, read_state, write_state


def stable_bigint(kind: str, name: str) -> str:
    value = int.from_bytes(hashlib.sha256(f"title-iq:{kind}:{name}".encode()).digest()[:8], "big")
    return str(1_000_000_000_000_000 + value % 8_000_000_000_000_000_000)


def stable_guid(kind: str, name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://github.com/regshih/fabric-data-agents-title-insurance-poc/{kind}/{name}"))


def part(path: str, payload: dict) -> dict:
    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    return {"path": path, "payload": encoded, "payloadType": "InlineBase64"}


def build_definition(workspace_id: str, lakehouse_id: str, display_name: str) -> tuple[dict, dict]:
    model = json.loads(Path("ontology/model.json").read_text(encoding="utf-8"))
    id_map = {"entities": {}, "relationships": {}}
    parts = [part("definition.json", {}), part(".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Ontology", "displayName": display_name},
        "config": {"version": "2.0", "logicalId": stable_guid("logical", display_name)},
    })]
    for entity_name, config in model["entities"].items():
        entity_id = stable_bigint("entity", entity_name)
        properties = []
        prop_ids = {}
        bindings = []
        for prop_name, (source_column, value_type) in config["columns"].items():
            prop_id = stable_bigint("property", f"{entity_name}.{prop_name}")
            prop_ids[prop_name] = prop_id
            properties.append({"id": prop_id, "name": prop_name, "redefines": None, "baseTypeNamespaceType": None, "valueType": value_type})
            bindings.append({"sourceColumnName": source_column, "targetPropertyId": prop_id})
        key_id = prop_ids[config["key"]]
        entity = {
            "id": entity_id, "namespace": "usertypes", "baseEntityTypeId": None, "name": entity_name,
            "entityIdParts": [key_id], "displayNamePropertyId": key_id, "namespaceType": "Custom",
            "visibility": "Visible", "properties": properties, "timeseriesProperties": [],
        }
        binding_id = stable_guid("binding", entity_name)
        binding = {"id": binding_id, "dataBindingConfiguration": {
            "dataBindingType": "NonTimeSeries", "propertyBindings": bindings,
            "sourceTableProperties": {"sourceType": "LakehouseTable", "workspaceId": workspace_id,
                                      "itemId": lakehouse_id, "sourceTableName": config["table"]},
        }}
        parts.append(part(f"EntityTypes/{entity_id}/definition.json", entity))
        parts.append(part(f"EntityTypes/{entity_id}/DataBindings/{binding_id}.json", binding))
        id_map["entities"][entity_name] = {"id": entity_id, "key": key_id, "properties": prop_ids, "binding": binding_id}
    for rel_name, (source_name, target_name, table, source_column, target_column) in model["relationships"].items():
        rel_id = stable_bigint("relationship", rel_name)
        context_id = stable_guid("contextualization", rel_name)
        relationship = {
            "namespace": "usertypes", "id": rel_id, "name": rel_name, "namespaceType": "Custom",
            "source": {"entityTypeId": id_map["entities"][source_name]["id"]},
            "target": {"entityTypeId": id_map["entities"][target_name]["id"]},
        }
        context = {
            "id": context_id,
            "dataBindingTable": {"sourceType": "LakehouseTable", "workspaceId": workspace_id,
                                 "itemId": lakehouse_id, "sourceTableName": table},
            "sourceKeyRefBindings": [{"sourceColumnName": source_column, "targetPropertyId": id_map["entities"][source_name]["key"]}],
            "targetKeyRefBindings": [{"sourceColumnName": target_column, "targetPropertyId": id_map["entities"][target_name]["key"]}],
        }
        parts.append(part(f"RelationshipTypes/{rel_id}/definition.json", relationship))
        parts.append(part(f"RelationshipTypes/{rel_id}/Contextualizations/{context_id}.json", context))
        id_map["relationships"][rel_name] = {"id": rel_id, "contextualization": context_id}
    return {"parts": parts}, id_map


def main() -> None:
    cfg = load_config()
    state = read_state()
    client = FabricClient()
    definition, id_map = build_definition(state["workspace_id"], state["lakehouse_id"], cfg.ontology_name)
    existing = client.find_item(state["workspace_id"], cfg.ontology_name, "Ontology")
    if existing:
        ontology_id = existing["id"]
        response = client.request("POST", f"workspaces/{state['workspace_id']}/items/{ontology_id}/updateDefinition?updateMetadata=true", json={"definition": definition})
    else:
        response = client.request("POST", f"workspaces/{state['workspace_id']}/items", json={
            "displayName": cfg.ontology_name,
            "type": "Ontology",
            "description": "Eight-entity business ontology for fictional title orders, properties, parties, instruments, encumbrances, commitments, policies, and offices.",
            "definition": definition,
        })
    result = client.wait_lro(response)
    ontology_id = existing["id"] if existing else ((result or {}).get("id") or client.find_item(state["workspace_id"], cfg.ontology_name, "Ontology")["id"])
    verify = client.request("POST", f"workspaces/{state['workspace_id']}/items/{ontology_id}/getDefinition")
    client.wait_lro(verify)
    Path("local-output").mkdir(exist_ok=True)
    Path("local-output/ontology-id-map.json").write_text(json.dumps(id_map, indent=2), encoding="utf-8")
    graph = next((x for x in client.list_all(f"workspaces/{state['workspace_id']}/items") if x["type"] == "GraphModel"), None)
    write_state({"ontology_id": ontology_id, "graph_item_id": graph["id"] if graph else None})
    print(json.dumps({"ontology_id": ontology_id, "graph_item_id": graph["id"] if graph else None, "parts": len(definition["parts"])}, indent=2))


if __name__ == "__main__":
    main()
