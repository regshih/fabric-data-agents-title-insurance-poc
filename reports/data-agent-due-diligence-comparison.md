# Fabric Data Agent due-diligence comparison

Test date: 2026-09-06 through 2026-09-07

## Executive result

All four configurations are published Fabric Data Agents. “Lakehouse-only” does not mean the app bypasses the agent: the agent translates natural language to SQL and queries the Lakehouse SQL analytics endpoint. The separate semantic model is Direct Lake.

The hybrid Data Agent was the most accurate tested configuration: 17 of 17 strict fact checks passed. The Lakehouse-only Data Agent was the fastest at a 16.60-second mean, but it missed all or part of two questions. The Ontology did not make every question better by itself; it was useful for relationship traversal, while the governed semantic model supplied reliable KPI logic. Combining those two sources produced the best result on this POC suite.

## Configurations tested

| Label | Published item | Sources | Runtime |
|---|---|---|---|
| Lakehouse-only | `title_insurance_direct_agent` | 19 selected Lakehouse tables; no Ontology | Standard |
| Ontology-only | `title_insurance_iq_agent` | `title_insurance_ontology` | Standard |
| Semantic-model-only | `title_insurance_semantic_agent` | Seven selected tables from `title_iq_sm` | Standard and Preview A/B |
| Hybrid | `title_insurance_hybrid_agent` | `title_iq_sm` plus `title_insurance_ontology` | Standard and Preview A/B |

The Data Agents themselves are no-code Fabric items. Python in this repository creates/configures the items, invokes their published MCP endpoints from another application, and runs repeatable evaluations; it does not replace the Fabric agent’s planning or query generation.

## Main controlled comparison

The same 17 unambiguous questions ran once against each agent on the dedicated F32 capacity. Every call used a fresh MCP session and the Standard runtime. The suite contains nine KPIs, two direct lookups, three relationships, and three operational decision questions. Expected facts were generated from the deterministic synthetic source data. Automated case-insensitive regular-expression checks were followed by human review of every hybrid answer and every non-passing answer from the other agents.

| Data Agent | Transport | Strict correct | Partial | Incorrect | Partial-credit score | Mean | p50 | p90 | p95 | Min | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Lakehouse-only | 17/17 | 15/17 (88.2%) | 1 | 1 | 91.2% | **16.60 s** | **14.72 s** | **19.31 s** | 26.22 s | 11.80 s | 35.60 s |
| Ontology-only | 17/17 | 14/17 (82.4%) | 0 | 3 | 82.4% | 17.93 s | 16.01 s | 20.24 s | **25.35 s** | 13.95 s | **36.23 s** |
| Semantic-model-only | 17/17 | 14/17 (82.4%) | 2 | 1 | 88.2% | 25.86 s | 20.86 s | 34.66 s | 43.81 s | 13.59 s | 73.77 s |
| Hybrid | 17/17 | **17/17 (100%)** | 0 | 0 | **100%** | 21.01 s | 19.73 s | 29.48 s | 33.48 s | **10.73 s** | 43.48 s |

This is one controlled POC run, not a production SLA or statistical proof. The results demonstrate what worked on the tested data and questions.

### Failure analysis

- Lakehouse-only returned the correct encumbrance ID and status for `ORDER000123` but omitted the requested type (`Judgment`), then abstained on the highest-average-risk county aggregation.
- Ontology-only rounded the requested 59.8-day average down to 59, could not recover from a generated Graph aggregate syntax error, and named the wrong county for the highest average risk.
- Semantic-model-only was perfect on all nine KPI questions and all three decision questions. Its deliberately narrow AI schema omitted party details and did not expose all relationship identifiers, so two relationship answers were partial and one was an appropriate abstention.
- Hybrid returned every required fact, including all three relationship traversals and all nine KPIs. Human review found no contradictory extra claim in those 17 answers.

Raw responses and machine-readable scores are in the matching `*-responses.csv`, `*-benchmark-summary.json`, and `*-accuracy.json` files in this directory. The test definition is `benchmark/due_diligence_questions.yaml`.

## Standard versus Preview runtime

The same representative eight-question subset ran with fresh sessions on both runtimes at F32.

| Agent | Runtime | Strict accuracy | Mean | p50 | p90 | Max | Observation |
|---|---|---:|---:|---:|---:|---:|---|
| Semantic-only | Standard | **8/8** | 24.56 s | 23.78 s | 29.62 s | 40.31 s | Accuracy winner |
| Semantic-only | Preview | 7/8 + 1 partial | **20.49 s** | **20.84 s** | **25.74 s** | **27.13 s** | 16.6% lower mean, but lost a relationship fact |
| Hybrid | Standard | 8/8 | 19.35 s | 19.48 s | 26.12 s | 28.31 s | GA/stable default |
| Hybrid | Preview | 8/8 | **18.11 s** | **18.56 s** | **20.24 s** | **20.37 s** | 6.4% lower mean in a small sample |

Standard remains the deployed recommendation. Microsoft describes Standard as GA and stable, while Preview changes more frequently. The observed hybrid Preview gain is too small and the sample too limited to promise a durable performance benefit. See [Fabric Data Agent runtime](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-runtime).

## Connection reuse

The hybrid Standard agent ran the same eight-question subset through one initialized MCP session. It remained 8/8 correct and averaged 17.87 seconds versus 19.35 seconds with fresh sessions, a 7.6% observed improvement. Median fell from 19.48 to 17.82 seconds.

This still uses the Fabric Data Agent for every question; it caches neither questions nor answers. The production Function keeps its HTTP connection pool and Azure credential/token cache warm, but retains a clean MCP session per request for failure isolation. The modest 7.6% mean gain did not justify adding cross-request MCP-session lifecycle and concurrency risk to this preview endpoint.

## Capacity experiment

The earlier controlled Ontology-agent sample used the same eight prompts at F16, F32, and F64: 28.79, 23.70, and 28.77 seconds mean respectively. F32 was 17.7% faster than F16; F64 was 21.4% slower than F32. Capacity therefore is not a linear latency knob. F32 remains the POC recommendation because it had the best measured mean and tail, but scaling above F32 did not help. See `capacity-performance-comparison.md` for the full table and caveats.

## Configuration improvements applied

- Limited each agent to the sources and tables needed for its role.
- Added explicit business definitions for “active,” exact `Open`, unresolved clearance, identifier prefixes, source routing, and relationship use.
- Added business-friendly semantic-model descriptions, relationships, and governed DAX measures for the tested KPIs.
- Validated the semantic measures directly after model refresh.
- Kept the model compact and the hybrid routing rules concise.
- Built a deterministic evaluation suite and preserved every raw response.

These changes follow Microsoft’s guidance to limit selected schema, describe objects, define terms and join paths, and add targeted examples where the source type supports them: [configuration best practices](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-configuration-best-practices), [data-source configuration matrix](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-add-datasources), and [semantic-model best practices](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices).

Verified Answers are a promising next semantic-model improvement for frequently asked questions, but they require authoring triggers from a Power BI report visual in Prep for AI. The public Data Agent configuration API does not create that report-bound artifact, so it was not silently claimed as applied. Microsoft also does not currently support example-query pairs directly on semantic-model or Ontology sources; Lakehouse sources do support them.

## External application result

The Azure Function uses a service principal to call the published MCP endpoint. With F32 active, the service principal returned the correct Lakehouse-only answer (`81`) in 23.74 seconds. It could invoke the other three Data Agent endpoints, but their downstream source tools returned 401 authorization errors for Ontology and semantic-model access. The semantic model had a verified explicit Read grant through the permitted `FabricAutomation` security group in addition to workspace Contributor access, so broader workspace access was not added.

The external app therefore enables only the proven Lakehouse-only path and displays the other three tested configurations as unavailable in that app. The four-way evidence and the Fabric-native user-identity demo remain available. Current Microsoft guidance requires both Data Agent access and explicit access to every source: [service-principal authentication](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-service-principal) and [sharing and permissions](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-sharing).

## Recommendation

1. Use the **hybrid Standard Data Agent** for the Fabric-native customer demonstration and for the most accurate tested behavior.
2. Use the **Lakehouse-only Standard Data Agent** in the external Function until Fabric’s preview service-principal path can query Ontology and semantic-model sources end to end.
3. Keep F32 for interactive POC demos; do not pay for F64 expecting lower latency based on this evidence.
4. Expect roughly 15–30 seconds for typical Data Agent responses and design the UI with progress feedback and a generous timeout.
5. Add Prep for AI Verified Answers through Power BI for the customer’s highest-value recurring KPI questions, then rerun the same ground-truth suite before production adoption.

