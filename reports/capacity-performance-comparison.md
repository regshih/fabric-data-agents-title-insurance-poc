# Fabric Data Agent capacity and connection comparison

Test date: 2026-09-06

Agent: Ontology-grounded `title_insurance_iq_agent`, Standard runtime

## Controlled capacity sample

The same eight deliberately mixed questions (`A01`, `A07`, `B01`, `B06`, `C01`, `C05`, `D01`, `D06`) ran once at each capacity size. Each measured call used a fresh MCP session after one unmeasured warm-up. The sample includes simple lookups, identifier-routing failures, aggregates, and expensive multi-hop requests, so it is heavier than the overall 32-question suite.

| Capacity | Calls | Mean | p50 | p90/p95 | Minimum | Maximum | Mean vs F16 |
|---|---:|---:|---:|---:|---:|---:|---:|
| F16 | 8 | 28.79 s | 25.74 s | 41.58 s | 15.26 s | 44.31 s | Baseline |
| F32 | 8 | 23.70 s | 23.75 s | 25.49 s | 15.68 s | 31.72 s | 17.7% faster |
| F64 | 8 | 28.77 s | 29.28 s | 36.52 s | 18.99 s | 40.03 s | 0.1% faster |

F32 was the best observed size, especially at the tail. F64 provided no further improvement and was 21.4% slower than F32 on this sample. Capacity is therefore not a linear latency control; orchestration, source query shape, tool selection, and model generation remain substantial parts of total time.

One observation per question cannot separate capacity effects from normal agent variability. Treat 17.7% as the observed POC result, not a guaranteed service-level improvement.

## Connection reuse sample

At F16, the same eight questions were run inside one initialized MCP session rather than opening a session for every question.

| Connection mode | Calls | Mean | p50 | p90/p95 | Minimum | Maximum | Mean change |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fresh session | 8 | 28.79 s | 25.74 s | 41.58 s | 15.26 s | 44.31 s | Baseline |
| Persistent session | 8 | 24.34 s | 19.92 s | 33.93 s | 13.92 s | 53.37 s | 15.5% faster |

Connection/session reuse improved the mean and median but did not eliminate server-side variability; the worst persistent-session call was slower. The Azure Function therefore reuses its HTTP connection pool and cached Azure credentials across warm invocations while creating a clean MCP session per request for isolation and recovery.

## Applied decision

- Keep the Data Agent Standard runtime and concise, source-specific instructions.
- Retain F32 as the recommended interactive-demo capacity; do not use F64 for this workload.
- Cache Key Vault secret retrieval, Entra credentials/tokens, and outbound HTTP connections in each warm Function worker.
- Use a progress-aware UI and a 110-second service timeout because even optimized tail latency is measured in tens of seconds.
- Do not expect capacity to repair accuracy. Improve accuracy with explicit identifier routing, relationship-path guidance, curated aggregates, and completeness/truncation rules.
- Pause the Fabric capacity outside demos; a paused capacity does not need to remain at the cheapest SKU to avoid compute charges.
