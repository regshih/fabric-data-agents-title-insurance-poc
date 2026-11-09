# Direct Lakehouse Data Agent evaluation

Evaluation date: 2026-09-05

Agent: `title_insurance_direct_agent`

Source: 19 selected managed tables in `title_iq_lh`; no Ontology or Graph source

Runtime: Standard on dedicated F16

Transport: published Fabric Data Agent MCP endpoint, one fresh MCP session per measured question after one warm-up

## Result

The agent works, but this configuration is not accurate enough for unattended operational use. It performed well on direct lookups and constrained joins, but poorly on several aggregates and broad relationship questions.

| Measure | Result |
|---|---:|
| Questions | 32 |
| MCP calls returning a response | 32/32 (100%) |
| Fully correct | 20/32 (62.5%) |
| Partially correct/incomplete | 3/32 (9.4%) |
| Incorrect or unable to answer | 9/32 (28.1%) |
| Partial-credit score (0.5 per partial) | 21.5/32 (67.2%) |
| Mean response time | 18.65 s |
| p50 | 17.58 s |
| p90 | 23.93 s |
| p95 | 25.07 s |
| Minimum | 11.65 s |
| Maximum | 42.63 s |

Interpretation: acceptable POC interactivity for most questions, but not "fast" for a chat UX without a progress indicator. The 42.6-second maximum and multi-second median justify an asynchronous/progress-aware external client.

## Accuracy by class

| Class | Question type | Fully correct | Partial | Incorrect |
|---|---|---:|---:|---:|
| A | Direct entity lookup | 7/8 | 0 | 1 |
| B | Constrained relationship traversal | 7/8 | 0 | 1 |
| C | Aggregation and KPI | 3/8 | 0 | 5 |
| D | Prioritization and broad multi-hop analysis | 3/8 | 3 | 2 |

## Question-level adjudication

| ID | Result | Evidence |
|---|---|---|
| A01-A06 | Correct | Returned the expected entity attributes and risk snapshot values. |
| A07 | Incorrect | Claimed `COMM000700` was missing; ground truth shows it exists with status `Revised`. |
| A08 | Correct | Returned `POLICY000900` type `Owner`. |
| B01-B05 | Correct | Returned the expected linked encumbrance, parties, office, instruments, and commitment. |
| B06 | Incorrect | Claimed `COMM000456` was missing; it is linked to issued `POLICY000456`. |
| B07-B08 | Correct | Returned the expected instrument and connected order entities. |
| C01 | Incorrect | Returned a generated-query error instead of the ground-truth count of 81 open High/Critical orders. |
| C02 | Incorrect | Claimed no Critical orders; open Critical orders exist in `OFFICE006` (1) and `OFFICE012` (2). |
| C03 | Correct | Top five open-order counties and counts matched ground truth. |
| C04 | Correct | Returned 59.8 days; ground truth is 59.8101. |
| C05 | Incorrect | Returned 2,120; ground truth is 1,928 unresolved required-clearance encumbrances. |
| C06 | Correct | All four risk-band counts matched exactly and totaled 5,000. |
| C07 | Incorrect | Returned zero; ground truth is 1,981 issued commitments connected to issued policies. |
| C08 | Incorrect | Returned no value; ground-truth average issued-policy premium is $2,773.71. |
| D01 | Partial | Correctly prioritized several highest-risk open orders, but only 7 of the deterministic top 10 were present under an explicit score/days-open tie break. |
| D02 | Correct | Correctly explained `ORDER000123` as score 30/Medium from its unresolved-clearance flag. |
| D03 | Partial | Returned 50 qualifying orders for 2026-09-05 through 2026-09-07; ground truth contains 72. |
| D04 | Correct | Returned all 44 open orders with both mismatch and unresolved-clearance flags. |
| D05 | Correct | Returned all 26 High/Critical orders with repeated search failures. |
| D06 | Incorrect | Claimed no matches; 292 properties have an active recorded lien and an open title order. |
| D07 | Partial | Returned exactly 200 order IDs without disclosing truncation; ground truth contains 302. |
| D08 | Incorrect | Could not join county and risk; Silver Pine has the highest average open-order risk score (21.14). |

## Method and limitations

- Response transport success is not treated as factual correctness.
- Expected facts were recomputed directly from the deterministic local Parquet files by `scripts/build_direct_agent_evaluation_facts.py`.
- Full correctness requires the requested result to agree with ground truth and not silently omit material rows.
- Partial responses receive 0.5 credit only in the explicitly labeled secondary score.
- One run per question is sufficient for a POC baseline, not for statistical production certification. Repeat runs are needed to measure answer variability.
- The test measures the direct Lakehouse configuration only. It does not establish the accuracy of the now-published Ontology agent.

Raw responses are in `reports/direct-agent-responses.csv`; calculated facts are in `reports/direct-agent-evaluation-facts.json`; timing statistics are in `reports/direct-agent-benchmark-summary.json`.
