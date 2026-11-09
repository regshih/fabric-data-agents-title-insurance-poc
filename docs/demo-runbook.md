# Demo runbook

1. Resume `fabrictitleiqpoc` and open workspace `fabric-iq-title-insurance-poc`.
2. In OneLake Catalog, search `title insurance`; show the Lakehouse, semantic model, notebooks, and pipeline descriptions.
3. Open `title_iq_lh`; show managed entity, relationship, risk snapshot, and data-quality tables.
4. Open `title_iq_sm`; show the operational KPI measures.
5. Open `title_insurance_ontology`; show eight entity types and traverse Order -> Property -> Instrument and Order -> Encumbrance.
6. Open the four published agents: Lakehouse-only, Ontology-only, semantic-model-only, and hybrid. Explain that every one is a Fabric Data Agent; “Lakehouse-only” is not an application-side Direct Lake shortcut.
7. Ask the hybrid agent one governed KPI and one relationship question. Recommended: “How many open High or Critical title orders are there?” and “List every party connected to ORDER000250; return PartyID and PartyType.”
8. Show `reports/data-agent-due-diligence-comparison.md`, including the 17-question accuracy/latency table, the Standard-versus-Preview A/B, and the F16/F32/F64 capacity result.
9. Launch the external Function. Explain that only the Lakehouse-only option is enabled because the service principal was proven end to end there; the other sources were tested successfully with a user identity but currently return downstream 401s for the app identity.
8. Run a controlled incremental generator/upload/build/Graph refresh, then confirm the new identifiers appear.
9. Pause the capacity after the demo.
