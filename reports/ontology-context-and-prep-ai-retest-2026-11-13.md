# Ontology context and Prep for AI follow-up: November 13, 2026

> Subsequent update: the Prep for AI + Verified Answers experiment described below as blocked was completed later the same day. See the [dedicated retest and measurements](prep-ai-verified-answers-retest-2026-11-13.md). The historical account below records the state of the earlier follow-up.

## Outcome

The current **Ontology-as-context** integration is now exercised, not merely inferred from documentation. A new, isolated Preview Data Agent (`title_insurance_ontology_context_agent`) was created and published against the existing Ontology and its bound `title_iq_lh` Lakehouse. It answered **17/17** deterministic questions correctly in one sequential pass, and **9/9** additional calls across three previously fragile questions. All 26 MCP calls completed. This is a promising accuracy result, but it was **slower** than the November 12 Standard agents and is too small a sample to establish a service-level reliability or latency claim.

The separately approved **semantic-model Prep for AI + Verified Answers** experiment was **not run**. The current semantic model's TMDL definition has no `Copilot/` Prep for AI parts. Microsoft currently documents Verified Answers as an interactive Power BI authoring feature and says REST API/CI/CD authoring is unsupported. The connected signed-in browser session was unavailable, so we did not manufacture a purported Verified Answers variant via undocumented payloads. This is a test gap, not a failed accuracy result.

## Method and comparable numbers

The new agent used the same synthetic data, West US 3 **F32**, signed-in user identity, 17-question gold set, sequential fresh MCP sessions, and one unmeasured warm-up as the [November 12 retest](data-agent-retest-2026-11-12.md). Times include connection/session setup, tool discovery, execution, and answer generation. The new integration requires Preview; the existing November agents ran on Standard. Configuration and runtime therefore both differ, so the rows are **observational comparisons, not a controlled estimate of Ontology's causal effect**.

| Agent / runtime | Strict accuracy | Transport | Mean | p50 | p90 | p95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lakehouse only / Standard, Nov 12 | 15/17 | 17/17 | 11.28 s | 9.51 s | 16.40 s | — | 22.86 s |
| Legacy Ontology-backed / Standard, Nov 12 | 14/17 | 17/17 | 13.13 s | 11.09 s | 13.14 s | — | 33.49 s |
| Semantic model only / Standard, Nov 12 | 16/17 | 17/17 | 13.07 s | 11.62 s | 16.52 s | — | 24.35 s |
| Semantic model + legacy Ontology / Standard, Nov 12 | 16/17 | 17/17 | 14.21 s | 11.41 s | 23.09 s | — | 26.53 s |
| Semantic model only / Preview, Nov 12 | 15/17 | 17/17 | 16.46 s | — | 22.81 s | — | 27.50 s |
| **New Ontology-as-context / Preview, Nov 13** | **17/17** | **17/17** | **16.56 s** | **15.48 s** | **21.63 s** | **23.17 s** | **29.16 s** |

On the three-question repeat (`R03`, `D01`, `D03`), the new agent passed **9/9** with **9/9** transport success; mean **15.86 s**, p90 **20.73 s**, max **20.74 s**. Across the full and repeat runs, each of those three questions passed **4/4**. By contrast, the previous hybrid's `R03` passed only **1/4** November 12 observations. The new agent correctly returned both parties for `ORDER000250`, the ten IDs in the required tie-break order, and Silver Pine at 21.14 for the highest Open-order county average. Manual inspection of the other first-pass answer summaries found no contradictory extra claims.

The automatic scorer initially rejected two **correct** new-agent answers because its expected regex accepted `59.81` but not `59.810126`, and `21.14` but not `21.140000`. The gold-set patterns now accept these equivalent display precisions. All five November 12 baseline response files were regraded with the corrected patterns; their strict scores above **did not change**. The scorer remains a deterministic-fact check, not a semantic judge or a substitute for reviewing generated queries and provenance.

## What the new agent actually used

The new agent was created using the current `fabric-data-agent-sdk` `add_staging_ontology` path, which attaches the Ontology as **context** and exposes its bound source for query execution. Its published item ID and runtime are stored in the local ignored environment state. This is not the blocked legacy `Ontology` add-as-data-source endpoint and does not change the pre-existing demo agents. The creation script is [create_ontology_context_agent.py](../scripts/create_ontology_context_agent.py); the agent-specific guidance is [title_insurance_ontology_context_instructions.md](../agent/title_insurance_ontology_context_instructions.md). The 0.1.36a0 SDK requires delegated user credentials for this management route. On this machine, x64 Python also needs `DOTNET_ROOT=C:\Program Files\dotnet\x64` when running that script.

Raw answers, latency summaries, and strict grades are saved under `ontology-context-agent-trial-2026-11-13-preview-f32-*` in this directory, including the `-repeat-*` files. The benchmark command was:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_agent.py --agent context --mode warm --connection-mode fresh --questions-file benchmark\due_diligence_questions.yaml --report-tag trial-2026-11-13-preview-f32 --checkpoint --resume
```

## Semantic-model Prep for AI / Verified Answers gap

The current model definition was read through Fabric's `getDefinition?format=TMDL` API and contained model/table/relationship parts, but no `Copilot/` parts. No clone, schema selection, AI instructions, Verified Answers, or semantic agent republish was performed in this follow-up. Microsoft's [semantic-model guidance for Data Agent](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices) says AI Data Schema, AI Instructions, and Verified Answers are relevant; it also notes that Data Agent uses a matched Verified Answer's information for DAX but does not return its visual. Microsoft's [Verified Answers authoring documentation](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-verified-answers) requires a report visual and Power BI Desktop/service authoring, and explicitly lists Git integration, REST APIs, and deployment pipelines as unsupported. Separately, [Power BI Copilot with Fabric IQ enabled](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-ask-data-question) does not return Verified Answers; that Power BI Copilot limitation should not be misrepresented as a measured Data Agent result.

To complete the second experiment, make a signed-in Power BI/Fabric browser tab available for interactive authoring. Create an isolated copy of the Direct Lake semantic model, constrain the AI Data Schema to the tables/columns needed by the gold questions, add concise business definitions in Prep for AI, create a report visual for one or two stable KPI questions, and set their Verified Answer trigger phrases. Attach only that model to a separate Data Agent, then rerun the same 17-question and targeted-repeat benchmark. Record the exact model configuration and test both exact and paraphrased triggers. Keep the existing semantic agent/model untouched for an A/B comparison.

The F32 was paused after testing. Local tests: **14 passed**; Ruff checks passed. No production or customer data was used.
