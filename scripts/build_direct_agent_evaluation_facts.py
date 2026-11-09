from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

DATA = Path("local-output/data")


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet")


def main() -> None:
    order = load("title_order")
    risk = load("order_risk_snapshot")
    commitment = load("commitment")
    policy = load("policy")
    encumbrance = load("encumbrance")
    instrument = load("recorded_instrument")
    property_df = load("property")
    rel_order_office = load("rel_order_office")
    rel_order_property = load("rel_order_property")
    rel_property_instrument = load("rel_property_instrument")
    rel_order_commitment = load("rel_order_commitment")
    rel_commitment_policy = load("rel_commitment_policy")

    open_risk = risk.merge(order[["order_id", "order_status"]], on="order_id")
    open_risk = open_risk[open_risk["order_status"] == "Open"]
    at_risk = open_risk[open_risk["risk_band"].isin(["High", "Critical"])]

    critical_by_office = (
        open_risk[open_risk["risk_band"] == "Critical"]
        .merge(rel_order_office, on="order_id")
        .groupby("office_id")
        .size()
        .sort_values(ascending=False)
        .to_dict()
    )
    counties = (
        order[order["order_status"] == "Open"]
        .merge(rel_order_property, on="order_id")
        .merge(property_df[["property_id", "county"]], on="property_id")
        .groupby("county")
        .size()
        .sort_values(ascending=False)
        .head(5)
        .to_dict()
    )
    unresolved = encumbrance[
        (encumbrance["encumbrance_status"] == "Open")
        & encumbrance["requires_clearance"]
        & ~encumbrance["release_recorded"]
    ]

    issued_commitment_policy = (
        commitment[commitment["commitment_status"] == "Issued"]
        .merge(rel_commitment_policy, on="commitment_id")
        .merge(policy[policy["policy_status"] == "Issued"][["policy_id"]], on="policy_id")
    )

    active_liens = instrument[
        (instrument["instrument_type"] == "Lien") & (instrument["instrument_status"] == "Active")
    ][["instrument_id"]]
    active_lien_open_orders = (
        active_liens.merge(rel_property_instrument, on="instrument_id")
        .merge(rel_order_property, on="property_id")
        .merge(order[order["order_status"] == "Open"][["order_id"]], on="order_id")
    )

    completed_without_issued_policy = (
        order[order["order_status"] == "Completed"][["order_id"]]
        .merge(rel_order_commitment, on="order_id")
        .merge(rel_commitment_policy, on="commitment_id", how="left")
        .merge(policy[["policy_id", "policy_status"]], on="policy_id", how="left")
    )
    completed_without_issued_policy = completed_without_issued_policy[
        completed_without_issued_policy["policy_status"].fillna("Missing") != "Issued"
    ]

    current_start = date(2026, 9, 5)
    current_end = date(2026, 9, 7)
    closing_without_issued_commitment = (
        order[(order["target_close_date"] >= current_start) & (order["target_close_date"] <= current_end)][
            ["order_id", "target_close_date"]
        ]
        .merge(rel_order_commitment, on="order_id", how="left")
        .merge(commitment[["commitment_id", "commitment_status"]], on="commitment_id", how="left")
    )
    closing_without_issued_commitment = closing_without_issued_commitment[
        closing_without_issued_commitment["commitment_status"].fillna("Missing") != "Issued"
    ]
    mismatch_and_clearance = open_risk[
        open_risk["ownership_or_vesting_mismatch"] & open_risk["unresolved_required_clearance_lien"]
    ]
    repeated_high_risk = risk[
        risk["repeated_search_failure"] & risk["risk_band"].isin(["High", "Critical"])
    ].sort_values(["risk_score", "days_open", "order_id"], ascending=[False, False, True])

    risk_by_county = (
        open_risk.merge(rel_order_property, on="order_id")
        .merge(property_df[["property_id", "county"]], on="property_id")
        .groupby("county")
        .agg(order_count=("order_id", "count"), average_risk_score=("risk_score", "mean"), total_risk_score=("risk_score", "sum"))
        .sort_values(["average_risk_score", "total_risk_score"], ascending=False)
    )

    facts = {
        "COMM000700": commitment.loc[commitment["commitment_id"] == "COMM000700"].to_dict("records"),
        "COMM000456_policy": (
            rel_commitment_policy[rel_commitment_policy["commitment_id"] == "COMM000456"]
            .merge(policy, on="policy_id")
            .to_dict("records")
        ),
        "open_high_or_critical_count": len(at_risk),
        "open_critical_by_office": {str(key): int(value) for key, value in critical_by_office.items()},
        "top_open_counties": {str(key): int(value) for key, value in counties.items()},
        "average_days_open_over_30": float(risk.loc[risk["days_open"] > 30, "days_open"].mean()),
        "unresolved_required_clearance_count": len(unresolved),
        "issued_commitments_with_issued_policy_count": len(issued_commitment_policy),
        "average_issued_policy_premium_dollars": float(policy.loc[policy["policy_status"] == "Issued", "premium_amount_cents"].mean() / 100),
        "top_open_orders": open_risk.sort_values(["risk_score", "days_open", "order_id"], ascending=[False, False, True])[
            ["order_id", "risk_score", "risk_band", "days_open"]
        ].head(10).to_dict("records"),
        "active_lien_open_order_property_count": int(active_lien_open_orders["property_id"].nunique()),
        "closing_2026_09_05_through_07_without_issued_commitment": closing_without_issued_commitment.sort_values(
            ["target_close_date", "order_id"]
        )[["order_id", "target_close_date", "commitment_id", "commitment_status"]].to_dict("records"),
        "open_mismatch_and_unresolved_clearance": mismatch_and_clearance.sort_values("order_id")[
            ["order_id", "risk_score", "risk_band", "blocking_issue_count", "days_open"]
        ].to_dict("records"),
        "high_or_critical_repeated_search_failure": repeated_high_risk[
            ["order_id", "risk_score", "risk_band", "blocking_issue_count", "days_open"]
        ].to_dict("records"),
        "completed_commitment_without_issued_policy_count": len(completed_without_issued_policy),
        "highest_average_risk_county": risk_by_county.head(1).reset_index().to_dict("records"),
    }
    target = Path("reports/direct-agent-evaluation-facts.json")
    target.write_text(json.dumps(facts, indent=2, default=str), encoding="utf-8")
    print(json.dumps(facts, indent=2, default=str))


if __name__ == "__main__":
    main()
