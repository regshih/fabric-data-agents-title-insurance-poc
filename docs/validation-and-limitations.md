# Validation and limitations

## Verified

- Dedicated West US 3 F16 Fabric capacity created in the selected subscription.
- Dedicated Fabric workspace, Lakehouse, two notebooks, Direct Lake semantic model, and pipeline created.
- Fast-tier parquet uploaded and materialized as 21 managed Delta/control tables.
- Local deterministic data tests passed; Fabric build and data-quality notebook runs completed.
- Lakehouse Tables API reported every expected table as `Managed` and `delta`.
- OneLake Catalog Search API returned success; descriptions were applied to supported items.
- The baseline pipeline run completed the build and validation.
- The incremental run completed after adding five synthetic tax liens; source row and risk changes are in `reports/incremental-change.json`.
- Fabric administrator access was confirmed through the tenant-settings API.
- Ontology preview was enabled only for a Fabric admins security group; Copilot and Copilot-capacity settings were already enabled.
- The Ontology and its child Graph were created, and the Graph refresh job completed.
- Ontology and direct-Lakehouse Data Agents were published and invoked through MCP.
- The workspace was assigned to domain `Title Insurance Analytics`.
- The no-Ontology agent completed all 32 benchmark calls; accuracy and latency are reported in `reports/direct-agent-evaluation.md`.

## Remaining manual or external boundaries

1. Connect Fabric Git to the GitHub repository interactively or supply a short-lived repository-scoped PAT through the process environment. The GitHub CLI OAuth token was tested without logging it and the Fabric connection API rejected it with `400`; it is not a PAT. Fabric Git support must not be inferred for Ontology, Graph, Data Agent, Lakehouse, or pipeline items absent current explicit support; scripts remain their source of truth.
2. External Power BI Execute Queries against the Direct Lake model returned a bodyless `400`; model creation is verified, but externally executed DAX measures are not.
3. The showcase web app is deployed with `azd up` from `azure.yaml` and `infra/`. Its unattended Data Agent call must use a service principal because the current Data Agent runtime does not support managed identity authentication.

The earlier Ontology, Data Agent, and domain blockers are closed. A full adjudicated Ontology-agent run and repeated/concurrent latency tests remain future measurement work rather than access blockers.
