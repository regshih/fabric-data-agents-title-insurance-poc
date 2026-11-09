# Implementation decisions

- The Fabric workspace is named `fabric-iq-title-insurance-poc`.
- West US 3 is the default region. A dedicated F16 keeps the POC isolated from other Fabric workloads and meets the planned baseline without premature F32/F64 scaling.
- The fast tier is the deployed tier. The scale tier is implemented but not run before the ontology/agent baseline.
- Eventhouse and unstructured RAG are omitted. Neither is necessary to prove the title-order relationship and risk scenario.
- The ontology has eight entities and eight useful directed relationships. Physical relationship tables remain explicit even though selected foreign keys are denormalized for the BI star model.
- Money is stored as integer cents, avoiding rounding and preview numeric ambiguity.
- The primary agent is ontology-only and uses Standard runtime. A second Standard-runtime agent connects directly to selected Lakehouse tables to provide the requested no-Ontology comparison. The semantic model remains separate for governed KPIs.
- Preview/API failures are recorded as manual-required until directly cleared; no capability is marked verified unless observed.
