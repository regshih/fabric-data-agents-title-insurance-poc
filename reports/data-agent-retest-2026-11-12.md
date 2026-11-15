# Fabric Data Agent retest: November 12, 2026

**Follow-up:** A new agent using the current Ontology-as-context integration was built and tested on November 13. See the [follow-up report](ontology-context-and-prep-ai-retest-2026-11-13.md); the migration blocker below describes the legacy API as observed on November 12, not the new SDK path.

## Decision

Keep this retest in the existing repository so the unchanged question suite, raw answers, October baseline, and configuration history remain together. **Semantic-model-only on Standard remains the most dependable customer demo**: 16/17 strict passes, 13.07-second mean, 16.52-second p90, and 17/17 transport success. The Lakehouse-only agent was faster but failed an entire risk-band distribution query. The hybrid matched semantic's single-pass score after ranking order was checked, but failed the party-relationship question in three subsequent checks; do not present it as reliably superior. These are observations from a small synthetic POC, not a production SLA or proof that a Fabric release caused the improvement.

## Controlled retest and comparable results

- Same West US 3 F32 capacity, workspace, four published agents, synthetic data, and [17-question suite](../benchmark/due_diligence_questions.yaml) as the [October retest](data-agent-retest-2026-10-07.md). The expected snapshot is dated September 1, 2026; the source tables were not fully diffed this month.
- Nine KPIs, two lookups, three relationships, and three decisions. One unmeasured warm-up per agent; one timed call per question with a fresh MCP session and the signed-in user identity. Calls were sequential, not concurrent or load-tested. Time includes connection/session setup, tool discovery, execution, and response generation.
- The scorer now checks the requested **order** of IDs in `D01`, in addition to deterministic facts. October's raw responses were re-scored with the same rule for the comparison below; the original October report and evidence are unchanged. Regex-based scores still require human review for negation, attribution, and unsupported claims.

| Published Standard agent | Oct strict | Nov strict | Nov transport | Oct mean | Nov mean | Mean change | Nov p50 / p90 / max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lakehouse only | 15/17 | 15/17 | 17/17 | 20.64 s | **11.28 s** | -45.3% | 9.51 / 16.40 / 22.86 s |
| Existing Ontology-backed | 15/17 | 14/17 | 17/17 | 19.69 s | 13.13 s | -33.3% | 11.09 / 13.14 / 33.49 s |
| Semantic model only | 16/17 | **16/17** | 17/17 | 20.67 s | 13.07 s | -36.8% | 11.62 / 16.52 / 24.35 s |
| Semantic model + Ontology | 15/17 | **16/17** | 17/17 | 21.51 s | 14.21 s | -34.0% | 11.41 / 23.09 / 26.53 s |

All four November means improved substantially on the unchanged F32 configuration. One pass per question cannot establish statistical significance, service-release attribution, or stable tail latency. In particular, the hybrid follow-up below shows why 17 transport successes and a good single-pass score are not enough.

## Answer review and repeatability

- **Lakehouse:** `K03` gave the correct counts (1 and 2) using office names instead of the expected OfficeIDs, so the strict scorer rejected it; a human could reasonably accept that answer. `K07` abstained because its query returned no rows, despite a populated risk snapshot and known band counts. Strict 15/17; reviewed exception-adjusted 16/17.
- **Ontology-backed:** `K05` rounded 59.8 days to 59. `R02` falsely said no matching open, required-clearance encumbrance existed for `ORDER000123`; the regex scorer called this partial solely because it found “Open” in the denial. `D03` selected Redwood County, 21, instead of Silver Pine County, 21.14. Strict and reviewed 14/17.
- **Semantic:** All nine KPIs, both lookups, and all three decisions passed. `R03` appropriately abstained because the selected seven-table semantic model has no party entity; it cannot fulfill that question. Strict and reviewed 16/17.
- **Hybrid:** `R01`, which falsely denied the policy relationship in October, now returned `POLICY000456` correctly. `D02` correctly attributed the 30-point Medium risk score to the unresolved required-clearance lien rather than unsupported factors. But `D01` returned the right ten IDs in **RiskScore then OrderID** order, ignoring the required DaysOpen tie-breaker; the tightened scorer rejects it. Strict and reviewed 16/17.
- **Hybrid spot-check after the full run:** `R03` failed once in a post-configuration check and in both repetitions of a four-call `R03,D01` follow-up, claiming a generated Lakehouse SQL/schema mismatch. It had passed in the initial full suite. `D01` was misordered in the first repeat and correct in the second. Thus `R03` passed 1 of 4 observed calls and `D01` passed 1 of 3. These follow-ups occurred after a blocked attempt to change hybrid staging configuration (no publish); they reveal fragility but do not isolate its cause. Inspect Fabric run steps and generated queries before changing routing.

## Standard versus Preview

| Semantic-model agent | Oct Preview | Nov Preview | Nov Standard |
|---|---:|---:|---:|
| Strict pass | 12/17 | 15/17 | **16/17** |
| Transport | 16/17 | 17/17 | 17/17 |
| All-call mean | 27.16 s | 16.46 s | **13.07 s** |
| p90 / max | 28.66 / 102.66 s | 22.81 / 27.50 s | **16.52 / 24.35 s** |

Preview improved versus its October run but did not beat November Standard. Preview `R03` remained out of scope. Its `D01` prose showed only six of ten requested IDs and embedded a serialized result-resource/CSV fragment instead of a clean complete ranked answer; the strict scorer rejected it. Semantic was republished to Standard after the test. [Microsoft distinguishes the stable Standard runtime from Preview's changing query and routing features](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-runtime), so Preview should be judged on this workload, not assumed faster.

**Hybrid Preview was not run.** Fabric rejected the repo's legacy Ontology `POST /staging/datasources` call with non-retriable `OntologyAddAsDataSourceBlocked`: “Ontologies can no longer be added as a data source. Add the ontology through the ontologies surface instead.” The script stopped before publishing, the staging runtime flag was reset to Standard, and a follow-up MCP response reported the published hybrid runtime as Standard. The repo now preflights for a legacy Ontology staging source before making staging changes. The existing published Ontology-backed agents were benchmarked, but a **new agent built using the current Ontology-as-context integration was not**. [Microsoft's current architecture](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-ontology-sources) treats Ontology as governed context and runs source-native SQL/KQL/DAX against underlying data; it recommends Preview for the best Ontology-context experience. Migrating this POC needs a separate agent/configuration and its own A/B test, not a silent rewrite of the legacy baseline.

## Updated implementation guidance

1. **Keep Standard semantic as the live demonstration path.** Its known limitation is party traversal, not broad KPI accuracy. The external Azure Function's app-identity path was not retested this month; these timings are MCP calls as the signed-in user, not browser end-to-end times or service-principal authorization proof.
2. **Move semantic-specific query guidance into Prep for AI.** The current semantic model has descriptions and a narrow table selection but no recorded AI Data Schema, Verified Answers, or Prep for AI instructions. [Microsoft's semantic-model guidance](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices) says DAX generation uses model metadata and Prep for AI, not agent-level DAX instructions; it also cautions that complex instructions can add latency. Configure a focused AI schema, explicit measures and definitions, and a few Verified Answers for stable KPIs in an isolated model variant, then rerun the suite.
3. **Treat Ontology as context in new work.** Add it through the current data-agent Sources experience, verify entity bindings and underlying query sources, refresh context after Ontology changes, and capture run steps for failures. [Current Ontology guidance](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-ontology-sources) says the requesting user needs permissions on the Ontology and underlying data; sharing the agent alone is insufficient. The old creation script cannot currently recreate the Ontology-backed agents with the new integration.
4. **Use diagnostics and stronger evaluations.** The repo's corrected ranking check caught a false pass. [Fabric's evaluation SDK and Diagnostics export](https://learn.microsoft.com/en-us/fabric/data-science/evaluate-data-agent) can capture run steps and generated queries to distinguish routing, schema, query, and answer-composition failures. Build a customer-facing gold set with multi-run pass rates and p95/p99 latency, including warm/cold and concurrent-user tests, before an SLA or migration decision. This SDK workflow was researched, not executed in this retest.
5. **Do not scale capacity just to chase these latencies.** This run held F32 fixed and found no capacity/throttling evidence. The [earlier F16/F32/F64 experiment](capacity-performance-comparison.md) did not show an F64 benefit on this workload. Fix source/query issues and measure capacity utilization before another paid scale trial.

## Evidence and operational status

Raw November responses, scorer outputs, and timing summaries are in this directory under `{direct|ontology|semantic|hybrid}-agent-retest-2026-11-12-standard-f32-*`, plus `semantic-agent-retest-2026-11-12-preview-f32-*` and `hybrid-agent-retest-2026-11-12-{post-block-check|repeat-f32}-*`. The benchmark and scorer are [benchmark_agent.py](../scripts/benchmark_agent.py) and [evaluate_due_diligence.py](../scripts/evaluate_due_diligence.py). All 14 local tests passed. The F32 capacity was confirmed **Paused** after the runs. No production data or customer tenant was used.
