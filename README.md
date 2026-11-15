# Fabric Data Agents: Title Insurance POC

An automation-first Microsoft Fabric proof of concept for title-order readiness and risk. It builds the
same synthetic data four ways and measures how well each Fabric Data Agent setup answers the same
due-diligence questions: Lakehouse-only, Ontology-only, semantic-model-only, and a hybrid of the
semantic model plus the Ontology.

Every record is deterministic synthetic data. The repository contains no real customer, borrower,
property, policy, or instrument data, and no tenant, subscription, or resource identifiers. Replace the
placeholders in `config/poc.yaml` or `.env` with your own values.

## Results

The same 17-question ground-truth suite (nine KPIs, two lookups, three relationship questions, three
operational decisions) ran once per question against all four published agents on the Standard runtime
at F32: in September, October, and November 2026.

| Agent setup | September | October | November 12 | November mean latency |
|---|---|---|---|---|
| Lakehouse-only | 15/17 | 15/17 | 15/17 | **11.28 s** |
| Ontology-only | 14/17 | 15/17 | 14/17 | 13.13 s |
| Semantic-model-only | 14/17 | **16/17** | **16/17** | 13.07 s |
| Hybrid (semantic model + Ontology) | **17/17** | 15/17 | **16/17** | 14.21 s |

October and November use the tightened scorer, which also checks the requested ranking order.

- The hybrid agent's perfect September score has not repeated. In November it scored 16/17, but the
  party-relationship question passed only 1 of 4 calls across the full run and follow-up checks.
- The semantic-model-only agent stayed the most dependable: 16/17 in October and November. It can't
  answer questions about entities outside its selected model, such as parties.
- All four agents were 33-45% faster in November than in October on the same F32 capacity. One run
  per question can't attribute that to a Fabric release.

### November follow-up experiments

| Experiment | Runtime | Result |
|---|---|---|
| New Ontology-as-context agent (Nov 13) | Preview | **17/17**, 16.56 s mean; 9/9 on three previously unstable questions |
| Same agent, rerun (Nov 14) | Preview | 15/17 after human review |
| Migrated, new-experience (TMDL) Ontology (Nov 14) | Preview | 15/17 after human review; one call failed. No accuracy gain over the original Ontology |
| Semantic model with Prep for AI, before and after one Verified Answer (Nov 13) | Standard | 16/17 both times. No measurable accuracy or latency gain |

- The Ontology-as-context integration is the first setup that answered the party-relationship
  question reliably (4 of 4 calls on Nov 13, and correct in every Nov 14 attempt). Its 17/17 did not
  repeat the next day, so treat it like the hybrid's September score: promising, not proven.
- The legacy way of adding an Ontology as a Data Agent source is now blocked by Fabric
  (`OntologyAddAsDataSourceBlocked`); new work should attach the Ontology as context.
- Capacity is not a linear latency control: the same prompts averaged 28.79 s at F16, 23.70 s at F32,
  and 28.77 s at F64.
- Each run is one call per question, not a production certification or SLA. Results changed between
  runs with no configuration changes, so re-run the suite before relying on any one result.

Details: [November 12 retest](reports/data-agent-retest-2026-11-12.md) (current),
[Ontology-as-context follow-up](reports/ontology-context-and-prep-ai-retest-2026-11-13.md),
[Prep for AI and Verified Answers](reports/prep-ai-verified-answers-retest-2026-11-13.md),
[old vs new Ontology experience](reports/ontology-new-experience-ab-retest-2026-11-14.md),
[October retest](reports/data-agent-retest-2026-10-07.md),
[September baseline](reports/data-agent-due-diligence-comparison.md),
[capacity comparison](reports/capacity-performance-comparison.md),
[Direct Lake Execute Queries resolution](reports/direct-lake-execute-queries-resolution.md), and
[validation and limitations](docs/validation-and-limitations.md).

## What gets built

| Item | Name |
|---|---|
| Fabric capacity | `fabrictitleiqpoc` (F16 to start; pause when idle) |
| Fabric workspace | `fabric-iq-title-insurance-poc` |
| Lakehouse | `title_iq_lh` (21 managed Delta/control tables) |
| Semantic model | `title_iq_sm` (Direct Lake) |
| Pipeline | `pl_title_iq_build_and_validate` |
| Ontology / Graph | `title_insurance_ontology` (eight entities, eight relationships) |
| Ontology data agent | `title_insurance_iq_agent` |
| Lakehouse-only data agent | `title_insurance_direct_agent` (19 Lakehouse tables, no Ontology) |
| Semantic-model-only data agent | `title_insurance_semantic_agent` |
| Hybrid data agent | `title_insurance_hybrid_agent` |
| Ontology-as-context data agent (Preview) | `title_insurance_ontology_context_agent` ([script](scripts/create_ontology_context_agent.py)) |
| Prep for AI trial (isolated copy) | `title_iq_sm_prep_ai_trial` + `title_insurance_semantic_agent_prep_ai_trial` ([script](scripts/create_prep_ai_trial.py)) |
| Optional external app | Azure Function on Flex Consumption with Entra sign-in ([runbook](docs/external-agent-app.md)) |

## Architecture

```text
deterministic generator -> Parquet -> OneLake Files -> managed Delta tables
                                               |-> Direct Lake KPI semantic model
                                               |-> direct Lakehouse Data Agent -> MCP benchmark
                                               |-> eight-entity Ontology definition
                                                        -> Graph child item
                                                        -> ontology-only Data Agent -> MCP benchmark
```

The fast tier contains 5,000 properties, 7,500 parties, 5,000 orders, 12,000 recorded instruments,
6,000 encumbrances, 4,000 commitments, and 3,500 policies. The scale tier is also implemented but is
intentionally not used until correctness and baseline performance are established.

## Reproduce

Prerequisites: an Azure subscription where you can create a Fabric capacity, Fabric tenant settings
that allow Ontology and Data Agents, and Python 3.10+. Set your subscription and tenant IDs in `.env`
(copy `.env.example`) or `config/poc.yaml` first; `manage_capacity.py` refuses to run if the signed-in
account doesn't match them.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,agent]"
az login
.\.venv\Scripts\python.exe scripts\manage_capacity.py ensure
.\.venv\Scripts\python.exe -m generator.generate --tier fast --mode reset
.\.venv\Scripts\python.exe scripts\provision_workspace.py
.\.venv\Scripts\python.exe scripts\upload_onelake.py
.\.venv\Scripts\python.exe scripts\deploy_notebooks.py --run
.\.venv\Scripts\python.exe scripts\create_semantic_model.py
.\.venv\Scripts\python.exe scripts\create_or_update_ontology.py
.\.venv\Scripts\python.exe scripts\refresh_ontology_graph.py
.\.venv\Scripts\python.exe scripts\create_or_update_data_agent.py
.\.venv\Scripts\python.exe scripts\create_or_update_direct_data_agent.py
.\.venv\Scripts\python.exe scripts\create_or_update_comparison_agent.py --agent semantic --runtime standard
.\.venv\Scripts\python.exe scripts\create_or_update_comparison_agent.py --agent hybrid --runtime standard
.\.venv\Scripts\python.exe scripts\benchmark_agent.py --agent direct
.\.venv\Scripts\python.exe scripts\benchmark_agent.py --agent ontology
.\.venv\Scripts\python.exe scripts\benchmark_agent.py --agent semantic --questions-file benchmark\due_diligence_questions.yaml
.\.venv\Scripts\python.exe scripts\benchmark_agent.py --agent hybrid --questions-file benchmark\due_diligence_questions.yaml
```

Run `scripts/manage_capacity.py pause` when the POC is idle. A Fabric capacity is billed while it runs.

For the Ontology-as-context experiment, install the optional `ontology-context` dependency, then run
`scripts/create_ontology_context_agent.py` and
`scripts/benchmark_agent.py --agent context --questions-file benchmark/due_diligence_questions.yaml`.
On x64 Python, set `DOTNET_ROOT` to your x64 .NET install first. For the semantic-model experiment, use
`scripts/create_prep_ai_trial.py`; authoring a Verified Answer is an interactive Power BI step.

## Safety and validation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe scripts\scan_secrets.py --history
```

CI runs the same checks on every pull request. See [SECURITY.md](SECURITY.md) for reporting issues.

Risk scores are operational-priority indicators only, not legal advice or underwriting decisions.

## License

[MIT](LICENSE)
