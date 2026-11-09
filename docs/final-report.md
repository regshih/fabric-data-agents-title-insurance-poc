# Final report

## Architecture

Built a GitHub repository, dedicated F32 capacity/workspace, OneLake Lakehouse, two Spark notebooks, orchestration pipeline, compact Direct Lake semantic model, eight-entity Ontology with refreshed Graph, and four published Data Agents. The agents isolate Lakehouse-only, Ontology-only, and semantic-model-only behavior, then combine the semantic model and Ontology in a native hybrid.

## Deployment inventory

| Resource | Name or ID | Observed state |
|---|---|---|
| Resource group | `rg-fabric-iq-title-poc-westus3` | Created |
| Fabric capacity | `fabrictitleiqpoc` (`F32`, West US 3) | Pause after validation and demos |
| Fabric workspace | `fabric-iq-title-insurance-poc` | Created |
| Lakehouse | `title_iq_lh` | Created; managed Delta |
| SQL endpoint | (with Lakehouse) | Created with Lakehouse |
| Semantic model | `title_iq_sm` | Created |
| Pipeline | `pl_title_iq_build_and_validate` | Created; two successful runs |
| Ontology | `title_insurance_ontology` | Created; eight entities and eight relationships |
| Graph | (Ontology child item) | Refresh completed in 133.6 seconds |
| Ontology agent | `title_insurance_iq_agent` | Published; Standard runtime |
| Direct agent | `title_insurance_direct_agent` | Published; 19 Lakehouse sources, no Ontology |
| Semantic agent | `title_insurance_semantic_agent` | Published; compact Direct Lake semantic model only |
| Hybrid agent | `title_insurance_hybrid_agent` | Published; semantic model plus Ontology |
| Domain | `Title Insurance Analytics` | Workspace assigned |

## Title-insurance domain model

Eight entities (Property, Party, TitleOrder, RecordedInstrument, Encumbrance, Commitment, Policy, AgentOffice), eight relationship types, stable string keys, and deterministic risk rules. Initial fast tier matched the requested counts; the deployed post-increment state contains 6,005 encumbrances after five synthetic tax liens were added.

## Verified Fabric IQ capabilities

Managed OneLake tables, notebook jobs, pipeline orchestration, Direct Lake semantic-model creation, item metadata, Catalog search, Ontology definition, Graph refresh, Data Agent publication, and MCP invocation were directly executed. The initial tenant-level `403` was cleared after the Fabric administrator role was activated and the Ontology preview setting was enabled for a Fabric admins security group.

## Agent accuracy

The earlier exploratory 32-question suite exposed ambiguity in both prompts and business definitions. A stricter 17-question ground-truth suite was then run identically against all four Standard agents at F32. Strict accuracy was 88.2% Lakehouse-only, 82.4% Ontology-only, 82.4% semantic-model-only, and 100% hybrid. The semantic agent was perfect on all nine KPIs but intentionally lacked some relationship fields; the hybrid recovered those relationships through the Ontology. See `reports/data-agent-due-diligence-comparison.md` and the raw response CSVs.

## Agent performance

All 68 main comparison calls returned through MCP. Mean end-to-end latency was 16.60 seconds Lakehouse-only, 17.93 seconds Ontology-only, 25.86 seconds semantic-model-only, and 21.01 seconds hybrid. A controlled hybrid session-reuse sample improved the mean from 19.35 to 17.87 seconds (7.6%) while remaining 8/8 correct. This is suitable for a progress-aware POC, not instant chat.

## Capacity finding

The same eight Ontology-agent prompts averaged 28.79 seconds at F16, 23.70 seconds at F32, and 28.77 seconds at F64. F32 was 17.7% faster than F16, while F64 was 21.4% slower than F32. F32 remains the measured POC recommendation; capacity is not a linear latency control and should remain paused outside active work.

## OneLake Catalog and governance

Catalog search succeeded and descriptions were applied. The data is labeled synthetic in names/descriptions and source. The workspace is assigned to the `Title Insurance Analytics` domain. Catalog discovery does not grant data access.

## Incremental refresh

Five fictional open tax liens (`ENC900001`-`ENC900005`) were added. Four orders moved from Low to Medium risk; a fifth remained Medium with a higher blocking count. Upload and the 281.3-second Fabric pipeline completed. A subsequent full Graph refresh completed successfully; a timed, pre/post incremental Graph visibility comparison was not run.

## Security

Working-tree and Git-history secret scans pass and run in CI. `.env`, generated Parquet, and local resource-state files are ignored. The GitHub OAuth token was held only in process memory during the failed Fabric Git connection attempt and was neither printed nor stored.

## Limitations

The accuracy results are single-run POC evidence, not production certification or an SLA. A service principal or user token is required to call the Data Agent MCP endpoint; managed identity is not currently supported for this runtime authentication path. The Function service principal works end to end for the Lakehouse-only agent. Ontology and semantic-model source tools currently return downstream 401 errors for that identity despite verified source/workspace permissions, so those app choices remain disabled and are demonstrated in Fabric with a user identity. Fabric Git still needs an actual GitHub PAT or interactive Fabric browser authorization. The earlier bodyless Direct Lake Execute Queries `400` was fixed; direct DAX validation now returns the expected governed measures.

## Cost

`fabrictitleiqpoc` is billable whenever active. Pause/resume tooling is included. F16, F32, and F64 were tested and the capacity was returned to F32. Pause it after active validation; the workspace and data remain available after resume.

## Demo runbook

Use `docs/demo-runbook.md`. Resume the capacity, compare all four agents and their grounded evidence, show the Graph relationships, launch the external Lakehouse-only app path, and pause the capacity when finished.
