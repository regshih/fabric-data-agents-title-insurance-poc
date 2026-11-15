# Prep for AI + Verified Answers retest — November 13, 2026

## Result

This previously blocked experiment was completed in a signed-in Power BI session. An isolated Direct Lake semantic model was configured with Prep for AI, a report card was published as a Verified Answer for the exact active-order question, and a separate Standard Data Agent queried only that semantic model. The original semantic model and agents were not changed.

The Verified Answer **did not increase full-suite accuracy** in this sample: both the before-Verified and after-Verified passes scored **16/17**, with **17/17 successful MCP calls** each. All nine KPI answers were correct in both passes. The only strict miss in each was `R03`, which asks for parties; the seven-table semantic model has no party entity. The agent explicitly said it could not retrieve party details and did not invent them. The separate Ontology-as-context agent in the [earlier follow-up](ontology-context-and-prep-ai-retest-2026-11-13.md) did answer that relationship question, but it is a different source and runtime.

| Same trial agent and F32 capacity | Strict facts | MCP success | Mean | Median | p90 | p95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prep for AI, before Verified Answer | 16/17 | 17/17 | 15.54 s | 12.44 s | 16.99 s | 35.72 s | 36.79 s |
| Prep for AI + one Verified Answer | 16/17 | 17/17 | 13.97 s | 14.07 s | 16.96 s | 17.97 s | 31.63 s |

The full-run mean was 1.57 seconds lower after publishing, but the median was 1.63 seconds higher. Different questions were the slow outliers in the two runs. With only one sequential pass per configuration, **there is no defensible causal speedup claim** from Verified Answers. The verified K01 question took 10.60 seconds before and 5.85 seconds after in those passes. Five further exact-trigger calls after publishing were **5/5 correct**, averaging **8.26 seconds** (5.60–9.76 seconds). Two unregistered paraphrases, each repeated three times, were **6/6 correct**, averaging **9.16 seconds** (8.37–9.53 seconds). Those are post-only measurements; they do not prove a Verified Answer effect over the already-good model measure.

## What was configured and tested

- Workspace: `fabric-iq-title-insurance-poc`, West US 3, F32 capacity. The capacity was resumed for testing and paused afterward.
- Isolated Direct Lake model: `title_iq_sm_prep_ai_trial`. It was cloned from the POC model, then refreshed/framed before source selection. Prep for AI's schema retained the seven queryable business tables; several irrelevant `title_order` fields/measures were deselected. Model-level AI instructions defined active statuses, measure preferences, dollars versus cents, risk ranking, and the missing-party limitation.
- Isolated Standard Data Agent: `title_insurance_semantic_agent_prep_ai_trial`. Its only source was the trial semantic model, with `agent_office`, `commitment`, `encumbrance`, `order_risk_snapshot`, `policy`, `property`, and `title_order` selected. It did **not** use an Ontology item.
- Verified Answer: a Power BI card using the existing `Open Title Orders` measure in report `title_iq_prep_ai_verified_kpis`. The exact K01 question was added as its trigger phrase and the answer appeared in the model's Verified Answers inventory. The card display abbreviated the value as `3K`; the Data Agent returned the exact **3,246** from the measure. A Data Agent uses matched Verified Answer information to form DAX but does not return the report visual itself, per [Microsoft's semantic-model guidance](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices).
- Benchmarks: the [17-question deterministic suite](../benchmark/due_diligence_questions.yaml), then [two paraphrases](../benchmark/prep_ai_verified_answer_questions.yaml) and five more exact-trigger calls. Each batch used one unmeasured warm-up and then sequential fresh MCP sessions. Timings include session setup, tool listing, execution, and answer generation, but not Azure CLI token acquisition. Automatic scoring checks deterministic facts; it is not a comprehensive semantic review.

The before-Verified run already had the AI schema and AI instructions. This isolates the Verified Answer better than comparing against last month's agent, but it does **not** measure the separate causal effects of schema simplification or AI instructions. The [November 12 unmodified semantic agent](data-agent-retest-2026-11-12.md) scored 16/17 with a 13.07-second mean on a different day; that row is contextual, not a same-day A/B control.

## Reproduction and evidence

`scripts/create_prep_ai_trial.py --stage model` creates the isolated model. Refresh/frame it in Power BI and set its AI Data Schema and AI instructions. In a report using that model, right-click the KPI card in Editing mode and choose **Set up a verified answer**; add the trigger and apply. Then run `scripts/create_prep_ai_trial.py --stage agent`. Verified Answer authoring currently requires the Power BI report experience; Microsoft documents [REST API, Git integration, and deployment pipelines as unsupported](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-verified-answers). The local agent-creation script does not claim to automate that part.

The raw response CSVs, benchmark summaries, and strict evaluations in this directory have these prefixes:

- `semantic-prep-ai-agent-pre-verified-2026-11-13-standard-f32`
- `semantic-prep-ai-agent-post-verified-2026-11-13-standard-f32`
- `semantic-prep-ai-agent-verified-exact-repeat-2026-11-13-standard-f32`
- `semantic-prep-ai-agent-verified-paraphrases-2026-11-13-standard-f32`

The batch command pattern was:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_agent.py --agent prep_ai --mode warm --connection-mode fresh --questions-file benchmark\due_diligence_questions.yaml --report-tag post-verified-2026-11-13-standard-f32 --checkpoint --resume
.\.venv\Scripts\python.exe scripts\evaluate_due_diligence.py reports\semantic-prep-ai-agent-post-verified-2026-11-13-standard-f32-responses.csv --output reports\semantic-prep-ai-agent-post-verified-2026-11-13-standard-f32-evaluation.json
```

The same command with the `pre-verified` tag was run before the answer was published. The exact repeat added `--question-ids K01 --repetitions 5`; the paraphrase run used `--questions-file benchmark\prep_ai_verified_answer_questions.yaml --repetitions 3`.

## Practical conclusion

Prep for AI and Verified Answers work end to end with the semantic-model Data Agent here. They are worthwhile for grounding named KPI questions and making the business meaning explicit, but this test does **not** show a measurable accuracy gain or reliable latency reduction over the already-correct semantic-model KPI path. Keep the Ontology-context path for entity relationships absent from the semantic model. If latency is a customer acceptance criterion, run larger randomized A/B batches with matched model versions, answer lengths, and source shapes before promising a speed target.

Local validation: `pytest` **14 passed**; Ruff checks passed. No production/customer data was used.
