# Fabric Data Agents: Title Insurance POC

An automation-first Microsoft Fabric proof of concept for title-order readiness and risk. It builds the
same synthetic data four ways and measures how well each Fabric Data Agent setup answers the same
due-diligence questions: Lakehouse-only, Ontology-only, semantic-model-only, and a hybrid of the
semantic model plus the Ontology.

Every record is deterministic synthetic data. The repository contains no real customer, borrower,
property, policy, or instrument data, and no tenant, subscription, or resource identifiers. Replace the
placeholders in `config/poc.yaml` or `.env` with your own values.

## Results

A 17-question ground-truth suite ran against all four published agents on the Standard runtime at F32.

| Agent setup | Strict accuracy | Mean latency |
|---|---|---|
| Lakehouse-only | 88.2% | 16.60 s |
| Ontology-only | 82.4% | 17.93 s |
| Semantic-model-only | 82.4% | 25.86 s |
| Hybrid (semantic model + Ontology) | 100% | 21.01 s |

- The semantic-model agent got every KPI right but lacked some relationship fields; the hybrid recovered
  them through the Ontology.
- Capacity is not a linear latency control: the same prompts averaged 28.79 s at F16, 23.70 s at F32,
  and 28.77 s at F64.
- These are single-run POC results, not a production certification or SLA.

Details: [four-agent due-diligence report](reports/data-agent-due-diligence-comparison.md),
[October 2026 retest](reports/data-agent-retest-2026-10-07.md) (Standard vs Preview runtimes),
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
