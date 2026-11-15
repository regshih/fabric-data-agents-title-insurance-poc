# Old vs new Ontology experience: controlled retest (November 14, 2026)

## Bottom line

This is the first POC test of the **new Ontology item experience**, not just the newer Ontology-as-context Data Agent integration. The existing `title_insurance_ontology` was confirmed by the Fabric API as **generation 1**. Fabric's in-product **Create copy** migration produced `title_insurance_ontology_NewExperience`, confirmed as **generation 2** with a TMDL definition. The original item and its agent were left unchanged. A separate Preview Data Agent was published for the generation-2 copy; both agents derived the same `title_iq_lh` Lakehouse source.

The new experience **worked**, but this small A/B does **not** establish an accuracy improvement. The two 17-question first passes each had 15 fully correct answers after human review. Generation 2's successful calls averaged 13.89 s versus 16.01 s for generation 1, but generation 2 also had one MCP call error. In two repeats each of four unstable questions, generation 1 had 7/8 fully correct and generation 2 had 6/8. Their repeat means differed by only 0.30 s. Do not present the faster first pass as a proven Ontology-generation speedup.

## Configuration and comparability

| Dimension | Generation 1 | Generation 2 |
|---|---|---|
| Ontology | `title_insurance_ontology` | `title_insurance_ontology_NewExperience` |
| Definition | Old entity-type JSON | New TMDL (`entities/*.tmdl`, `entityRelationships.tmdl`, backing `tables/*.tmdl`) |
| Data Agent | `title_insurance_ontology_context_agent` | `title_insurance_ontology_v2_context_agent` |
| Bound data exposed to agent | `title_iq_lh` | `title_iq_lh` |
| Agent instructions/runtime | Same instructions, Preview | Same instructions, Preview |

Both tests used the same synthetic data, user identity, West US 3 F32 capacity, 17-question gold set, sequential fresh MCP sessions, and one unmeasured warm-up per run. The generation-1 full pass ran first, followed by generation 2; the targeted repeats ran in the opposite order. Latency includes connection/session setup, tool discovery, execution, and answer generation. Calls were not randomized or interleaved, and the sample is small.

The copied definition contained eight entity files, eight primary data tables, eight relationship backing tables, `relationships.tmdl`, and `entityRelationships.tmdl`. Fabric's completion screen said bindings, entity types, and relationships were copied. This confirms structural migration, not semantic equivalence of every generated query or rule. No business rules or Activator alerts were in this POC migration.

## Results

| Run | Strict scorer | Human-reviewed interpretation | MCP success | Mean successful latency | p50 | p90 |
|---|---:|---|---:|---:|---:|---:|
| Gen 1, full 17 | 15 correct, 2 partial | 15 correct; 1 partial; 1 incorrect | 17/17 | 16.01 s | 15.24 s | 17.76 s |
| Gen 2, full 17 | 15 correct, 1 partial, 1 incorrect | Same | 16/17 | 13.89 s | 13.87 s | 15.80 s |
| Gen 1, four questions × 2 | 7 correct, 1 partial | Same | 8/8 | 13.96 s | 13.54 s | 15.81 s |
| Gen 2, four questions × 2 | 6 correct, 2 partial | Same | 8/8 | 13.66 s | 12.73 s | 14.75 s |

The full-run generation-2 mean is 2.12 s (13.2%) lower on successful calls. It excludes the failed 13.57 s MCP call, so it is not an apples-to-apples all-call success-adjusted measure. Across all four files, gen 1 returned 25/25 calls and gen 2 returned 24/25. With 17-question and eight-question runs this small, percentiles are descriptive, not reliability or SLO estimates.

### Question-level findings

- All nine KPI questions were fully correct in both full passes. The party-relationship question `R03` was also correct for both; this POC's Ontology includes the Party entity and its Lakehouse binding, unlike the limited semantic-model-only party test.
- `L02` (`COMM000700` status) was **wrong** in the gen-1 full pass: it said no record was found, when the gold answer is `Revised`. The strict pattern scorer marked it partial because it repeated the ID, but human review treats that answer as incorrect. Gen 2 answered it correctly in its full pass. Both agents answered it correctly in both repeats, indicating stochastic behavior rather than a consistent generation-specific capability.
- `R01` (policy resulting from `COMM000456`) produced an MCP error in the gen-2 full pass. Both generation-2 repeats and all generation-1 attempts returned the correct policy details. The captured error did not identify a root cause.
- `D01` (top ten Open orders by RiskScore, DaysOpen, OrderID) was correct for both generations in all measured attempts. The returned gen-2 answer put the complete list in an MCP CSV resource representation with literal escaped line breaks. The old scorer incorrectly treated `\\r\\nORDER...` as a word-character boundary and rejected seven IDs. The evaluator now normalizes those line breaks before matching; both full-pass files were regraded. This changes only the gen-2 D01 grade from incorrect to correct.
- `D02` (explain `ORDER000123` risk drivers) remained the weak reasoning question. Gen 2 gave score `30` and band `Medium` but omitted the required unresolved-clearance explanation in all three attempts. Gen 1 omitted it in the full pass and one repeat, but included it in one repeat. Both versions queried order-level flags; better ontology modeling or agent guidance may be needed to make the encumbrance-to-risk explanation reliable. Do not treat a plausible explanation as proof of the deterministic score formula.

## Reproduce and next best-practice experiment

The new item was created with the Fabric UI **Create copy** action, not by reusing the repo's old-generation JSON authoring script. `scripts/create_ontology_context_agent.py --new-experience` creates/publishes the isolated comparison agent; `scripts/benchmark_agent.py --agent context_v2` selects it. IDs are in ignored `local-output/environment-state.json` on this machine. The raw response CSVs, benchmark summaries, and accuracy JSONs use the `v1-baseline`, `v2-migrated`, and `targeted-repeat` prefixes in this directory.

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_agent.py --agent context_v2 --mode warm --connection-mode fresh --questions-file benchmark\due_diligence_questions.yaml --report-tag v2-migrated-2026-11-14-preview-f32 --checkpoint --resume
.\.venv\Scripts\python.exe scripts\evaluate_due_diligence.py --questions-file benchmark\due_diligence_questions.yaml reports\ontology-v2-context-agent-v2-migrated-2026-11-14-preview-f32-responses.csv
```

For a larger customer-facing claim, rerun multiple randomized/interleaved passes on the same capacity, separate transport failures from answer failures, and manually audit generated queries and resource attachments. A distinct follow-up could enrich the new Ontology with explicit risk-driver meaning and retest `D02`, but that would change both the model and prompt context and should be reported as a separate intervention, not attributed to migration alone. Keep the original Ontology and agent until consumers have been validated against the new item. Microsoft's [migration guidance](https://learn.microsoft.com/en-us/fabric/iq/ontology/overview#migrate-from-old-experience) says downstream consumers must be reconnected, and its [new definition documentation](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition) describes TMDL and item-definition ALM support.
