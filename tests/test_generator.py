from generator.generate import TIERS, generate_dataset


def test_fast_tier_counts_and_synthetic_provenance() -> None:
    tables = generate_dataset("fast", seed=42)
    tier = TIERS["fast"]
    assert len(tables["property"]) == tier.properties
    assert len(tables["party"]) == tier.parties
    assert len(tables["title_order"]) == tier.orders
    assert len(tables["recorded_instrument"]) == tier.instruments
    assert len(tables["encumbrance"]) == tier.encumbrances
    assert len(tables["commitment"]) == tier.commitments
    assert len(tables["policy"]) == tier.policies
    assert all(frame["is_synthetic"].all() for frame in tables.values())


def test_relationship_endpoints_and_risk_bounds() -> None:
    t = generate_dataset("fast", seed=42)
    pairs = [
        ("rel_order_property", "order_id", "title_order", "order_id"),
        ("rel_order_property", "property_id", "property", "property_id"),
        ("rel_order_party", "party_id", "party", "party_id"),
        ("rel_property_instrument", "instrument_id", "recorded_instrument", "instrument_id"),
        ("rel_order_encumbrance", "encumbrance_id", "encumbrance", "encumbrance_id"),
        ("rel_order_commitment", "commitment_id", "commitment", "commitment_id"),
        ("rel_commitment_policy", "policy_id", "policy", "policy_id"),
    ]
    for rel, rel_key, entity, entity_key in pairs:
        assert set(t[rel][rel_key]).issubset(set(t[entity][entity_key]))
    assert t["order_risk_snapshot"]["risk_score"].between(0, 100).all()
    assert set(t["order_risk_snapshot"]["risk_band"]) <= {"Low", "Medium", "High", "Critical"}


def test_generation_is_deterministic() -> None:
    first = generate_dataset("fast", seed=7)
    second = generate_dataset("fast", seed=7)
    assert first["title_order"].equals(second["title_order"])
    assert first["order_risk_snapshot"].equals(second["order_risk_snapshot"])

