# Fabric Data Agent retest: October 7, 2026

## Decision

Keep the existing repository and retain the September report as a historical baseline. The current **semantic-model-only Standard** agent is the strongest tested option for governed KPIs and decisions: 16/17 strict fact checks, 20.67-second mean, and no transport errors. It cannot answer the party relationship question because that entity is outside its selected model. The hybrid agent's September 17/17 result did **not** repeat: it scored 15/17 on Standard, including a false denial of a real commitment-to-policy link and an unsupported risk explanation. Do not present the hybrid agent as the most accurate current configuration until those cases are fixed and retested.

This is one run per question in each configuration. Changes from September are observed differences, not proof that a particular Fabric release caused them or a production latency guarantee.

## Controlled setup

- Same dedicated West US 3 F32 capacity, Fabric workspace, four published agent items, synthetic dataset, and [17-question suite](../benchmark/due_diligence_questions.yaml) as the [September comparison](data-agent-due-diligence-comparison.md).
- Nine KPI, two lookup, three relationship, and three operational decision questions. The source snapshot and expected facts remain dated September 1, 2026. Core counts in the new answers agree with the existing ground truth; a full Lakehouse data-diff was not run.
- One unmeasured warm-up per agent, followed by one timed call per question using a fresh MCP session and the signed-in user identity. Calls were sequential, not a load test. Times include session setup, tool discovery, Fabric execution, and answer generation.
- Standard was tested on all four agents. Semantic-model-only and hybrid were then republished temporarily on Preview and tested on the same 17 questions. Both were republished back to Standard afterward. No model, Ontology, source-selection, or instruction edits were made for this A/B test.
- The benchmark now checkpoints each answer and can resume after interruption. Failed-call time is reported separately and in `all_call_latency`; the older `mean` field remains a success-only metric for compatibility.

## September versus October: Standard runtime

The accuracy columns below show automated exact-fact checks. Manual exception review is explained after the tables. A positive time change is slower.

| Agent source | September strict | October strict | October manual exception review | September mean | October mean | Change | October p50 / p90 / max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lakehouse only | 15/17 | 15/17 | 16/17 | 16.60 s | 20.64 s | +4.04 s (+24.3%) | 18.50 / 30.30 / 35.38 s |
| Ontology only | 14/17 | 15/17 | 15/17 | 17.93 s | 19.69 s | +1.76 s (+9.8%) | 17.49 / 24.31 / 34.86 s |
| Semantic model only | 14/17 | **16/17** | **16/17** | 25.86 s | 20.67 s | **-5.19 s (-20.1%)** | 20.05 / 28.78 / 31.67 s |
| Semantic model + Ontology | **17/17** | 15/17 | 15/17 | 21.01 s | 21.51 s | +0.50 s (+2.4%) | 20.09 / 26.90 / 46.59 s |

All 68 Standard calls returned through the MCP transport. The Lakehouse was no longer the clear speed winner; Lakehouse, Ontology, and semantic-model means clustered around 20 seconds. The old hybrid accuracy advantage was not reproduced.

## Current Standard versus Preview

These are all-call latency statistics, including time spent on failed calls. The semantic Preview call for `D01` failed with a Fabric MCP internal error after 102.66 seconds. The earlier success-only summary would otherwise hide that delay.

| Agent | Runtime | Automated strict | Manual exception review | Transport | Mean | p50 | p90 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Semantic model | Standard | 16/17 | 16/17 | 17/17 | **20.67 s** | 20.05 s | 28.78 s | 31.67 s |
| Semantic model | Preview | 12/17 | 12/17 | 16/17 | 27.16 s | 20.12 s | 28.66 s | **102.66 s** |
| Hybrid | Standard | 15/17 | 15/17 | 17/17 | **21.51 s** | 20.09 s | **26.90 s** | 46.59 s |
| Hybrid | Preview | 16/17 | 15/17 | 17/17 | 23.74 s | **19.06 s** | 42.14 s | 54.41 s |

Preview did not earn a deployment change on this test. Microsoft documents [Standard as GA and Preview as a faster-changing runtime](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-runtime); Preview's advanced DAX path can improve some cases but is not guaranteed to be faster or more accurate for this model. The published semantic and hybrid agents were restored to Standard.

## Answer review and test limitations

- **Lakehouse Standard:** `R02` returned the right encumbrance ID and status but omitted the requested type (`Judgment`). `D02` correctly attributed the 30-point Medium score to `unresolved_required_clearance_lien = True`. The regex checker marked `D02` partial because its expected pattern accepts spaces or hyphens but not underscores. Manual exception review counts it correct; the original automated score remains unchanged for an exact comparison.
- **Ontology Standard:** `K05` rounded 59.8 days to 59. `D03` chose Redwood County and 21 instead of Silver Pine County and 21.14. All three relationship checks passed.
- **Semantic Standard:** `R03` correctly stated that party data is absent from the selected semantic model, so it could not supply the requested party IDs and types. That is a sensible abstention but fails the requested fact check. All nine KPIs, both lookups, and three decisions passed.
- **Hybrid Standard:** `R01` said there was no policy linked to `COMM000456`, although `POLICY000456` exists and the semantic-only agent found it. The answer refers to an Ontology lookup; this suggests a source or relationship-query failure, but MCP answer text alone does not prove the exact internal route. `D02` supplied the score and band but attributed risk to days open, expedite priority, and transaction type instead of the actual unresolved required-clearance lien. Those extra claims make the explanation unsafe to reuse as a grounded example.
- **Semantic Preview:** `K03` returned office counts that ignored the requested exact `Open` filter, `R02` falsely said no matching encumbrance existed, `R03` could not answer the out-of-scope party question, `D01` returned an internal error, and `D02` could not retrieve a known order's risk details. The regex checker called `R02` partial only because it found the word `Open` in an incorrect denial.
- **Hybrid Preview:** `R01` recovered the policy link, but `D02` falsely claimed the relevant risk-driver flags were unavailable and substituted a blocking-issue explanation. The regex checker counted it correct because it mentioned the phrase “unresolved required-clearance” while denying the fact; manual review rejects that answer. `D03` returned no county or average and attributed the failure to capacity. That capacity diagnosis was part of the agent's answer, not independently verified telemetry.

The exact-fact checker is useful for repeatability but cannot detect negation, unsupported causal explanations, missing ordering, or contradictory extra claims. The `D01` ranking answers that returned data were checked for the requested ID order as well as ID presence. All 17 semantic Standard answers and every non-passing answer in the other runs were reviewed for obvious contradictions; this was not an independent, blinded second adjudication. A single run cannot establish significance; repeat the preferred configuration across several runs and capture Fabric run steps before giving a customer a reliability claim.

## Better practice opportunities

1. **Prepare the semantic model where the DAX tool reads context.** The repo defines descriptive columns, measures, and a compact seven-table agent selection, but `scripts/create_semantic_model.py` does not configure Power BI Prep for AI's AI data schema, AI instructions, or Verified Answers. The current semantic-agent instruction file places definitions such as “active” and measure preferences at the agent level. [Microsoft's semantic-model guidance](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices) says the DAX generation tool uses model metadata and Prep for AI, and ignores agent-level instructions for DAX generation. Move the semantic-specific rules into Prep for AI, align its selected schema with the agent, add Verified Answers for recurring KPI questions, and rerun the same suite. This is a proposed next experiment, not a change applied in this retest.
2. **Diagnose hybrid routing with run steps.** Inspect the source and generated query for `R01` and `D02` in Fabric's run-step view. Make the Ontology source description narrower around party/instrument traversals and make the semantic model's scope clear for commitment-policy and risk-flag questions. Microsoft's [routing guidance](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-routing) recommends focused schema, source descriptions, representative examples where supported, and concise routing rules. The existing hybrid agent already has a routing rule, yet `R01` failed; more prose alone should not be assumed to fix it.
3. **Use SQL-specific context in a separate experiment.** The Lakehouse agent selects 19 tables. Audit which columns and relationship tables the 17 questions truly require. [Schema object descriptions and Topics](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-configurations) are Preview-only options for SQL sources, and [Build agent with AI](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-creator-agent-overview) can help draft SQL-source instructions and example queries. Review generated changes and test them in a separate agent/configuration so the Standard baseline remains available. These features do not configure Ontology or semantic-model Prep for AI.
4. **Keep configuration and results versioned.** Fabric's [Data Agent Git integration](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-source-control) can track published and draft agent configuration, including schema selections and examples. Continue keeping dated raw responses, accuracy JSON, timing summaries, and manual-review notes in this repo. Use a separate branch or workspace for configuration experiments when the customer demo must remain stable.
5. **Do not scale capacity as a first latency fix.** This retest held F32 constant. The [prior F16/F32/F64 experiment](capacity-performance-comparison.md) found F32 fastest in its small sample and no benefit from F64. Retest capacity only after query shape, model scope, and source routing are corrected; capture utilization and throttling evidence alongside timings.

## Operational status and evidence

- F32 capacity was confirmed **Paused** at the end of the retest.
- The semantic and hybrid agent scripts recorded `standard` as the restored published runtime. The staging settings read API returned AI instructions but did not echo the experimental flag, so the runtime restoration was not independently confirmed by a live post-restore query.
- The Azure Function's app-identity path was **not retested**. The local Azure CLI identity could list its settings but could not read the app credential from Key Vault. This retest therefore does not establish whether the earlier downstream 401 behavior has changed.
- Each configuration has a matching `*-responses.csv`, `*-accuracy.json`, and `*-benchmark-summary.json` in this directory, with the prefix `{direct|ontology|semantic|hybrid}-agent-retest-2026-10-07-{standard|preview}-f32`. The benchmark code is `scripts/benchmark_agent.py`; the scorer is `scripts/evaluate_due_diligence.py`.

Recommended next measured experiment: fix or constrain hybrid routing for `R01` and risk attribution for `D02`, configure semantic Prep for AI, then rerun the unchanged 17-question Standard suite at least three times. Preserve the current outputs as the before state.
