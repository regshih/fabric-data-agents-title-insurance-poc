# Product capability verification

Verified against Microsoft documentation and the authenticated tenant through **2026-09-05**.

| Capability | Current documented behavior | POC observation |
|---|---|---|
| Fabric IQ | Fabric IQ combines OneLake data, semantic models, and operational intelligence; the IQ workload is preview. | OneLake and semantic model created. |
| Ontology | Ontology and its definition APIs are preview. Entity/property/relationship definitions and OneLake bindings are supported. | Preview setting enabled for `FabricAdmins`; eight-entity Ontology created by REST. |
| Binding sources | Static bindings support managed Lakehouse tables. OneLake security, external tables, and Delta column mapping are unsupported. | All binding sources are managed Delta tables with safe lower-case names. |
| Graph refresh | Upstream changes require graph refresh. The child Graph item can have an automatic schedule and consumes capacity. | Child Graph created; full refresh completed in 133.6 seconds. |
| Data Agent | Requires paid F2+ and the Copilot/Azure OpenAI tenant settings. Supports ontology and Lakehouse sources. | Dedicated F16 and tenant settings verified; one Ontology agent and one direct Lakehouse agent published. |
| Agent configuration | Ontology sources support agent instructions and a source description, but not schema selection, per-source instructions, or example queries. | Instructions are versioned and deliberately concise. |
| Runtime | Standard is GA/default; Preview changes orchestration/tools and can be selected by SDK. | Standard used for both published agents; no ungrounded runtime comparison. |
| SDK and runtime API | Published agents are queried through MCP. Assistants-based querying was deprecated in August 2026 in favor of MCP/Responses. | Current public REST management surfaces and MCP 2.1.1 transport were executed successfully. |
| Semantic model | REST supports TMSL/TMDL definitions; Direct Lake is supported over OneLake. | `title_iq_sm` created by REST with a compact TMSL definition. |
| Git integration | GitHub is supported. Current source-code format explicitly lists notebooks and semantic models; unsupported items are not synchronized. | Ontology/Data Agent definitions remain source-controlled through scripts, not claimed as Fabric Git-supported items. |
| OneLake Catalog | Catalog Search API is preview; it discovers authorized metadata but does not grant data authorization. | Search returned success and item descriptions were updated. |
| Domain | Admin domain APIs require tenant-level permission. | Activating the Fabric administrator role cleared the API; workspace assigned to the title-insurance domain. |
| Capacity | Ontology modeling, AI tokens, Graph cache/operations, refresh, Spark, and semantic models can consume capacity. Pause/resume is supported. | Dedicated F16 created with pause tooling; no scale-up performed. |

## First-party sources

- [Fabric IQ overview](https://learn.microsoft.com/en-us/fabric/iq/overview)
- [Ontology overview](https://learn.microsoft.com/en-us/fabric/iq/ontology/overview)
- [Ontology tenant settings](https://learn.microsoft.com/en-us/fabric/iq/ontology/overview-tenant-settings)
- [Bind ontology data](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data)
- [Ontology REST API](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items)
- [Ontology capacity consumption](https://learn.microsoft.com/en-us/fabric/iq/ontology/resources-capacity-usage)
- [Data Agent tenant settings](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-tenant-settings)
- [Data Agent sources/configuration matrix](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-add-datasources)
- [Data Agent runtime](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-runtime)
- [Data Agent Python SDK and MCP endpoint](https://learn.microsoft.com/en-us/fabric/data-science/fabric-data-agent-sdk)
- [Data Agent service-principal authentication](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-service-principal)
- [Semantic model definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/semantic-model-definition)
- [Fabric Git source-code format](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/source-code-format)
- [OneLake Catalog REST overview](https://learn.microsoft.com/en-us/rest/api/fabric/articles/onelakecatalog/overview)
