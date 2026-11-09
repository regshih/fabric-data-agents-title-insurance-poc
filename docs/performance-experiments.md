# Performance experiments

| Experiment | Dataset | Runtime | Capacity | Result | Decision |
|---|---|---|---|---|---|
| P00 data build | Fast | n/a | F16 | Pipeline completed in 326.4 seconds, including Spark session/activity overhead | Source is ready for ontology binding; this is not agent latency. |
| P00b incremental source | Fast + 5 issues | n/a | F16 | Pipeline completed in 281.3 seconds; quality checks passed | Source incremental path verified. |
| P01 direct-agent baseline | Fast + 5 issues | Standard | F16 | 32/32 MCP responses; mean 18.65 s, p50 17.58 s, p90 23.93 s, p95 25.07 s, max 42.63 s | Use a progress-aware client and at least a 60-second request budget. Accuracy, not transport, is the immediate constraint. |
| P02 direct-agent accuracy | Fast + 5 issues | Standard | F16 | 20/32 fully correct (62.5%); 3 partial; 9 incorrect/unable | Direct Lake is credible for lookups/traversals, but needs stronger grounding for aggregates and broad joins. |
| P03 Graph refresh | Fast + 5 issues | n/a | F16 | Completed in 133.6 seconds | Ontology bindings are operational. |
| P04 Ontology-agent smoke | Fast + 5 issues | Standard | F16 | 4/4 MCP responses; mean 18.11 s, p50 17.07 s, max 22.84 s | Transport is operational; run the full adjudicated suite before claiming an accuracy improvement. |
| P05 four-agent due diligence | Fast + 5 issues | Standard | F32 | Lakehouse 88.2% / 16.60 s; Ontology 82.4% / 17.93 s; semantic model 82.4% / 25.86 s; hybrid 100% / 21.01 s | Recommend hybrid for Fabric user identity and Lakehouse-only for the currently proven external app identity. |
| P06 runtime A/B | Representative 8 questions | Standard vs Preview | F32 | Semantic Preview 16.6% faster but lost one fact; hybrid Preview 6.4% faster with equal sample accuracy | Keep Standard for stable behavior; Preview result is directional only. |
| P07 hybrid session reuse | Representative 8 questions | Standard | F32 | Persistent session 17.87 s vs fresh 19.35 s, both 8/8 | 7.6% gain is real but modest; retain per-request MCP isolation in the Function. |

The benchmark measures end-to-end MCP latency. It does not isolate source-query time, model generation, Graph time, or capacity queuing. These one-pass POC samples are evidence, not a production SLA. Full details and raw artifacts are in `reports/data-agent-due-diligence-comparison.md`.
