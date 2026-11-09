# Architecture and domain model

The authoritative layer is `title_iq_lh`, a Lakehouse of curated managed Delta tables. Eight entity tables bind to Ontology; eight relationship mapping tables bind graph edges. `order_risk_snapshot`, `property_title_summary`, and `daily_title_operations` avoid repeatedly reconstructing common logic.

The eight ontology entities are Property, Party, TitleOrder, RecordedInstrument, Encumbrance, Commitment, Policy, and AgentOffice. Relationships are `concerns`, `involves`, `has_recorded`, `has_issue`, `creates_or_supports`, `produces`, `results_in`, and `handles`.

`title_iq_sm` is a compact Direct Lake KPI model with explicit measures, business descriptions, and a narrow Data Agent schema. It supports both the semantic-model-only comparison and the hybrid experiment.

`title_insurance_iq_agent` uses only the Ontology. `title_insurance_direct_agent` uses 19 selected Lakehouse tables and no Ontology. `title_insurance_semantic_agent` uses only `title_iq_sm`. `title_insurance_hybrid_agent` combines the semantic model for governed KPIs with the Ontology for relationship questions. Their published MCP endpoints are the programmatic measurement surface. Client latency, source/Graph work, and capacity signals are reported separately.

Eventhouse was omitted because the static operational scenario already demonstrates relationship traversal, risk prioritization, KPIs, and refresh. Adding an event source before the ontology baseline would increase graph/runtime complexity without improving the core proof.
