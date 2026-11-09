# Ontology Data Agent evaluation

Evaluation date: 2026-09-06

Agent: `title_insurance_iq_agent`

Source: `title_insurance_ontology` and its refreshed Graph

Runtime: Standard on dedicated F16

Transport: published Fabric Data Agent MCP endpoint, one fresh MCP session per measured question after one warm-up

## Result

The Ontology configuration did not improve overall full-answer accuracy in this single-run baseline. It materially improved aggregate/KPI answers but regressed on constrained traversal and broad multi-hop questions.

| Measure | Ontology | Direct Lakehouse | Difference |
|---|---:|---:|---:|
| Questions returning a response | 32/32 | 32/32 | Equal |
| Fully correct | 20/32 (62.5%) | 20/32 (62.5%) | Equal |
| Partially correct/incomplete | 2/32 (6.3%) | 3/32 (9.4%) | -1 partial |
| Incorrect or unable | 10/32 (31.3%) | 9/32 (28.1%) | +1 incorrect |
| Partial-credit score | 21/32 (65.6%) | 21.5/32 (67.2%) | -1.6 points |
| Mean response time | 23.32 s | 18.65 s | +4.67 s (25.0% slower) |
| p50 | 20.32 s | 17.58 s | +2.74 s |
| p90 | 36.05 s | 23.93 s | +12.12 s |
| p95 | 41.58 s | 25.07 s | +16.51 s |
| Maximum | 48.01 s | 42.63 s | +5.38 s |

These are separate single runs on the same F16 and data, not paired repeated trials. They establish a POC result, not a statistically stable production ranking.

## Accuracy by class

| Class | Question type | Ontology correct | Ontology partial | Ontology incorrect | Direct correct |
|---|---|---:|---:|---:|---:|
| A | Direct entity lookup | 7/8 | 0 | 1 | 7/8 |
| B | Constrained relationship traversal | 6/8 | 0 | 2 | 7/8 |
| C | Aggregation and KPI | 6/8 | 0 | 2 | 3/8 |
| D | Prioritization and broad multi-hop analysis | 1/8 | 2 | 5 | 3/8 |

## Question-level adjudication

| ID | Result | Evidence |
|---|---|---|
| A01-A06 | Correct | Returned the expected entity attributes. |
| A07 | Incorrect | Treated commitment ID `COMM000700` as an order ID and claimed it was absent; it exists with status `Revised`. |
| A08 | Correct | Returned policy type `Owner`. |
| B01 | Incorrect | Reported no unresolved blocker and cited cleared `ENC003364`; ground truth is open required-clearance judgment `ENC003216`. |
| B02-B05 | Correct | Returned the expected parties, office, instruments, and commitment. |
| B06 | Incorrect | Treated `COMM000456` as an order ID and missed issued `POLICY000456`. |
| B07-B08 | Correct | Returned the expected supporting instrument and connected entities. |
| C01 | Correct | Returned 81 open High/Critical orders, including 3 Critical. |
| C02 | Incorrect | Claimed zero Critical orders; `OFFICE006` has 1 and `OFFICE012` has 2. |
| C03 | Incorrect | Grouped county and state combinations; the requested county-only ranking is Bluebird 262, Redwood 259, Silver Pine 250, Lakeshore 248, Northstar 240. |
| C04-C08 | Correct | Returned the expected average days open, clearance count, risk distribution, issued commitment/policy count, and average premium. |
| D01 | Partial | Returned ten numbered issues but only three unique orders; it omitted seven of the deterministic top ten. |
| D02 | Correct | Correctly explained score 30 from the open required-clearance judgment and included the operational-risk disclaimer. |
| D03 | Incorrect | Explicitly declined to produce the requested date-window result. |
| D04 | Incorrect | Claimed no matches; ground truth contains 44 open mismatch plus unresolved-clearance orders. |
| D05 | Incorrect | Attributed repeated-search failures to numerous orders that do not have that flag; only a small subset overlapped the 26 ground-truth orders. |
| D06 | Partial | Returned valid representative property/order/lien triples but not the complete set of 292. |
| D07 | Incorrect | Returned 120; ground truth is 302 completed orders with a commitment and no issued policy. |
| D08 | Incorrect | Selected Bluebird; Silver Pine has the highest average open-order risk score at 21.14. |

## Interpretation

The Ontology helps when the question aligns with a clearly modeled aggregate or relationship path, as shown by the aggregate improvement from 3/8 to 6/8. It does not eliminate query-planning, identifier-routing, truncation, or over-broad traversal errors. The main next accuracy work should add narrower agent instructions and curated aggregate views, plus explicit identifier prefixes and result-completeness rules; buying more capacity is not an accuracy remedy.

Raw answers and timings are in `reports/ontology-agent-f16-full-responses.csv`. Deterministic facts are in `reports/direct-agent-evaluation-facts.json` because both agents were tested against the same source state.
