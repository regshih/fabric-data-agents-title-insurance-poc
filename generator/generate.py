from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from title_iq.risk import score_orders


@dataclass(frozen=True)
class Tier:
    properties: int
    parties: int
    orders: int
    instruments: int
    encumbrances: int
    commitments: int
    policies: int


TIERS = {
    "fast": Tier(5_000, 7_500, 5_000, 12_000, 6_000, 4_000, 3_500),
    "scale": Tier(25_000, 35_000, 25_000, 75_000, 30_000, 20_000, 18_000),
}

COUNTIES = ["Northstar", "Lakeshore", "Redwood", "Silver Pine", "Bluebird"]
MUNICIPALITIES = ["Exampleton", "Fiction Falls", "Demo Harbor", "Sample Heights", "Testville"]
STATES = ["PA", "OH", "NC", "TX", "AZ"]


def ids(prefix: str, count: int, width: int = 6) -> np.ndarray:
    return np.array([f"{prefix}{i:0{width}d}" for i in range(1, count + 1)], dtype=object)


def _dates(as_of: pd.Timestamp, offsets: np.ndarray) -> pd.Series:
    return pd.Series(as_of + pd.to_timedelta(offsets, unit="D")).dt.date


def generate_dataset(tier_name: str = "fast", seed: int = 42, as_of_date: str = "2026-09-01") -> dict[str, pd.DataFrame]:
    if tier_name not in TIERS:
        raise ValueError(f"tier must be one of {sorted(TIERS)}")
    n = TIERS[tier_name]
    rng = np.random.default_rng(seed)
    as_of = pd.Timestamp(as_of_date)
    synthetic = True

    property_ids = ids("PROP", n.properties)
    party_ids = ids("PARTY", n.parties)
    order_ids = ids("ORDER", n.orders)
    instrument_ids = ids("INST", n.instruments)
    encumbrance_ids = ids("ENC", n.encumbrances)
    commitment_ids = ids("COMM", n.commitments)
    policy_ids = ids("POLICY", n.policies)
    office_ids = ids("OFFICE", 12, 3)

    prop = pd.DataFrame({
        "property_id": property_ids,
        "parcel_id": ids("PARCEL", n.properties),
        "fictional_address": [f"{100+i} Example Avenue" for i in range(n.properties)],
        "municipality": rng.choice(MUNICIPALITIES, n.properties),
        "county": rng.choice(COUNTIES, n.properties),
        "state": rng.choice(STATES, n.properties),
        "property_type": rng.choice(["SingleFamily", "Condominium", "Townhome", "Commercial"], n.properties, p=[.55,.2,.15,.1]),
        "current_vesting_type": rng.choice(["Sole", "Joint", "Trust", "Entity"], n.properties),
        "is_synthetic": synthetic,
    })
    party = pd.DataFrame({
        "party_id": party_ids,
        "synthetic_display_name": [f"Fictional Party {i:06d}" for i in range(1, n.parties + 1)],
        "party_type": rng.choice(["Buyer", "Seller", "Lender", "Trustee", "Organization"], n.parties),
        "state": rng.choice(STATES, n.parties),
        "is_synthetic": synthetic,
    })
    office = pd.DataFrame({
        "office_id": office_ids,
        "office_name": [f"Demo Title Office {i:03d}" for i in range(1, 13)],
        "region": rng.choice(["East", "Central", "South", "West"], 12),
        "service_tier": rng.choice(["Standard", "Priority"], 12, p=[.75,.25]),
        "is_synthetic": synthetic,
    })
    opened_offsets = -rng.integers(1, 91, n.orders)
    opened = pd.to_datetime(_dates(as_of, opened_offsets))
    target = opened + pd.to_timedelta(rng.integers(10, 46, n.orders), unit="D")
    status = rng.choice(["Open", "Search", "CommitmentIssued", "Completed", "Cancelled"], n.orders, p=[.25,.22,.18,.30,.05])
    order = pd.DataFrame({
        "order_id": order_ids,
        "opened_date": opened.dt.date,
        "target_close_date": target.dt.date,
        "order_status": status,
        "order_type": rng.choice(["Purchase", "Refinance", "Equity"], n.orders, p=[.55,.35,.1]),
        "transaction_type": rng.choice(["Residential", "Commercial"], n.orders, p=[.88,.12]),
        "priority": rng.choice(["Normal", "Expedite", "Critical"], n.orders, p=[.75,.2,.05]),
        "search_effective_date": (opened + pd.to_timedelta(rng.integers(1, 10, n.orders), unit="D")).dt.date,
        "ownership_vesting_mismatch": rng.random(n.orders) < .12,
        "repeated_search_failure": rng.random(n.orders) < .08,
        "is_synthetic": synthetic,
    })
    rel_order_property = pd.DataFrame({"order_id": order_ids, "property_id": property_ids[: n.orders]})
    primary_party = rng.choice(party_ids, n.orders, replace=not n.parties >= n.orders)
    extra_orders = rng.choice(order_ids, size=n.orders // 3, replace=False)
    extra_parties = rng.choice(party_ids, size=n.orders // 3, replace=False)
    rel_order_party = pd.DataFrame({
        "order_id": np.concatenate([order_ids, extra_orders]),
        "party_id": np.concatenate([primary_party, extra_parties]),
    }).drop_duplicates()
    rel_order_office = pd.DataFrame({"order_id": order_ids, "office_id": rng.choice(office_ids, n.orders)})
    order["office_id"] = rel_order_office["office_id"]

    instrument_property = rng.choice(property_ids, n.instruments)
    instrument = pd.DataFrame({
        "instrument_id": instrument_ids,
        "instrument_type": rng.choice(["Deed", "Mortgage", "Lien", "Judgment", "Release", "Easement"], n.instruments),
        "recorded_date": _dates(as_of, -rng.integers(0, 3650, n.instruments)),
        "recording_reference": [f"SYN-REC-{i:08d}" for i in range(1, n.instruments + 1)],
        "instrument_status": rng.choice(["Active", "Released", "Superseded"], n.instruments, p=[.65,.25,.1]),
        "amount_cents": rng.integers(10_000_00, 80_000_000, n.instruments, dtype=np.int64),
        "is_synthetic": synthetic,
    })
    rel_property_instrument = pd.DataFrame({"property_id": instrument_property, "instrument_id": instrument_ids})

    enc_orders = rng.choice(order_ids, n.encumbrances)
    enc_instruments = rng.choice(instrument_ids, n.encumbrances, replace=False)
    enc_status = rng.choice(["Open", "Cleared", "Waived"], n.encumbrances, p=[.47,.45,.08])
    requires_clearance = rng.random(n.encumbrances) < .7
    encumbrance = pd.DataFrame({
        "encumbrance_id": encumbrance_ids,
        "encumbrance_type": rng.choice(["Mortgage", "TaxLien", "Judgment", "MechanicsLien", "Easement", "VestingException"], n.encumbrances),
        "exception_category": rng.choice(["Requirement", "StandardException", "ScheduleBException"], n.encumbrances),
        "encumbrance_status": enc_status,
        "requires_clearance": requires_clearance,
        "release_recorded": (enc_status == "Cleared") & (rng.random(n.encumbrances) < .85),
        "amount_cents": rng.integers(1_000_00, 50_000_000, n.encumbrances, dtype=np.int64),
        "is_synthetic": synthetic,
    })
    encumbrance["order_id"] = enc_orders
    rel_order_encumbrance = pd.DataFrame({"order_id": enc_orders, "encumbrance_id": encumbrance_ids})
    rel_instrument_encumbrance = pd.DataFrame({"instrument_id": enc_instruments, "encumbrance_id": encumbrance_ids})

    commitment_orders = order_ids[: n.commitments]
    commitment = pd.DataFrame({
        "commitment_id": commitment_ids,
        "commitment_number": [f"SYN-CMT-{i:07d}" for i in range(1, n.commitments + 1)],
        "issued_date": _dates(as_of, -rng.integers(0, 60, n.commitments)),
        "commitment_status": rng.choice(["Draft", "Issued", "Revised", "Cancelled"], n.commitments, p=[.1,.67,.18,.05]),
        "requirement_count": rng.integers(0, 8, n.commitments),
        "exception_count": rng.integers(0, 10, n.commitments),
        "is_synthetic": synthetic,
    })
    commitment["order_id"] = commitment_orders
    rel_order_commitment = pd.DataFrame({"order_id": commitment_orders, "commitment_id": commitment_ids})
    policy = pd.DataFrame({
        "policy_id": policy_ids,
        "policy_number": [f"SYN-POL-{i:07d}" for i in range(1, n.policies + 1)],
        "policy_type": rng.choice(["Owner", "Lender"], n.policies),
        "issued_date": _dates(as_of, -rng.integers(0, 45, n.policies)),
        "policy_status": rng.choice(["Issued", "Pending", "Voided"], n.policies, p=[.86,.1,.04]),
        "coverage_amount_cents": rng.integers(10_000_000, 150_000_000, n.policies, dtype=np.int64),
        "premium_amount_cents": rng.integers(50_000, 500_000, n.policies, dtype=np.int64),
        "is_synthetic": synthetic,
    })
    policy["commitment_id"] = commitment_ids[: n.policies]
    rel_commitment_policy = pd.DataFrame({"commitment_id": commitment_ids[: n.policies], "policy_id": policy_ids})

    open_required = encumbrance.assign(order_id=enc_orders).query(
        "requires_clearance and encumbrance_status == 'Open'"
    ).groupby("order_id").size()
    late_instrument_orders = set(rng.choice(order_ids, n.orders // 10, replace=False))
    has_commitment = set(commitment_orders)
    days_open = (as_of - opened).dt.days
    open_mask = np.isin(status, ["Open", "Search", "CommitmentIssued"])
    close_in = (target - as_of).dt.days
    features = pd.DataFrame({
        "order_id": order_ids,
        "unresolved_required_clearance_lien": [open_required.get(x, 0) > 0 for x in order_ids],
        "ownership_or_vesting_mismatch": order["ownership_vesting_mismatch"],
        "instrument_after_search_effective_date": [x in late_instrument_orders for x in order_ids],
        "closing_within_three_days_without_commitment": [(0 <= d <= 3) and oid not in has_commitment for oid, d in zip(order_ids, close_in)],
        "past_service_level_target": open_mask & (days_open > 30),
        "repeated_search_failure": order["repeated_search_failure"],
        "blocking_issue_count": [int(open_required.get(x, 0)) for x in order_ids],
        "days_open": days_open,
        "snapshot_date": as_of.date(),
        "is_synthetic": synthetic,
    })
    risk = score_orders(features)
    order = order.merge(risk[["order_id", "risk_score", "risk_band", "blocking_issue_count", "days_open", "is_at_risk"]], on="order_id")

    daily = order.groupby(["opened_date", "order_status", "risk_band"], observed=True).agg(
        order_count=("order_id", "count"), at_risk_count=("is_at_risk", "sum"), average_days_open=("days_open", "mean")
    ).reset_index().rename(columns={"opened_date": "operation_date"})
    daily["is_synthetic"] = synthetic
    prop_summary = rel_order_property.merge(order[["order_id", "order_status", "risk_score", "risk_band", "blocking_issue_count"]], on="order_id")
    prop_summary = prop_summary.merge(prop[["property_id", "county", "state", "current_vesting_type"]], on="property_id")
    prop_summary["is_synthetic"] = synthetic

    tables = {
        "property": prop, "party": party, "agent_office": office, "title_order": order,
        "recorded_instrument": instrument, "encumbrance": encumbrance, "commitment": commitment, "policy": policy,
        "rel_order_property": rel_order_property, "rel_order_party": rel_order_party,
        "rel_property_instrument": rel_property_instrument, "rel_order_encumbrance": rel_order_encumbrance,
        "rel_order_commitment": rel_order_commitment, "rel_commitment_policy": rel_commitment_policy,
        "rel_order_office": rel_order_office, "rel_instrument_encumbrance": rel_instrument_encumbrance,
        "order_risk_snapshot": risk, "daily_title_operations": daily, "property_title_summary": prop_summary,
    }
    for frame in tables.values():
        if "is_synthetic" not in frame.columns:
            frame["is_synthetic"] = synthetic
    return tables


def write_dataset(tables: dict[str, pd.DataFrame], out_dir: Path, mode: str = "reset") -> dict[str, int]:
    if mode not in {"reset", "append", "incremental"}:
        raise ValueError("mode must be reset, append, or incremental")
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for name, frame in tables.items():
        path = out_dir / f"{name}.parquet"
        if mode == "append" and path.exists():
            frame = pd.concat([pd.read_parquet(path), frame], ignore_index=True).drop_duplicates()
        elif mode == "incremental" and path.exists():
            existing = pd.read_parquet(path)
            key_cols = [c for c in frame.columns if c.endswith("_id")][:1]
            frame = pd.concat([existing, frame], ignore_index=True)
            if key_cols:
                frame = frame.drop_duplicates(subset=key_cols, keep="last")
        frame.to_parquet(path, index=False)
        counts[name] = len(frame)
    (out_dir / "manifest.json").write_text(json.dumps({"mode": mode, "counts": counts}, indent=2), encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic fictional title-insurance data")
    parser.add_argument("--tier", choices=sorted(TIERS), default="fast")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date(2026, 9, 1))
    parser.add_argument("--mode", choices=["reset", "append", "incremental"], default="reset")
    parser.add_argument("--out", type=Path, default=Path("local-output/data"))
    args = parser.parse_args()
    counts = write_dataset(generate_dataset(args.tier, args.seed, args.as_of_date.isoformat()), args.out, args.mode)
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
