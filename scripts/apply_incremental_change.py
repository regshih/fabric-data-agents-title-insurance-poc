from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from title_iq.risk import score_orders


def main() -> None:
    root = Path("local-output/data")
    enc = pd.read_parquet(root / "encumbrance.parquet")
    new_ids = [f"ENC9{i:05d}" for i in range(1, 6)]
    if set(new_ids).issubset(set(enc["encumbrance_id"])):
        print("incremental change already applied")
        return
    order_ids = [f"ORDER{i:06d}" for i in range(1, 6)]
    instrument_ids = [f"INST{i:06d}" for i in range(1, 6)]
    additions = pd.DataFrame({
        "encumbrance_id": new_ids, "encumbrance_type": ["TaxLien"] * 5,
        "exception_category": ["Requirement"] * 5, "encumbrance_status": ["Open"] * 5,
        "requires_clearance": [True] * 5, "release_recorded": [False] * 5,
        "amount_cents": [2_500_000, 3_000_000, 3_500_000, 4_000_000, 4_500_000],
        "is_synthetic": [True] * 5, "order_id": order_ids,
    })
    pd.concat([enc, additions], ignore_index=True).to_parquet(root / "encumbrance.parquet", index=False)
    rel_order = pd.read_parquet(root / "rel_order_encumbrance.parquet")
    pd.concat([rel_order, pd.DataFrame({"order_id": order_ids, "encumbrance_id": new_ids, "is_synthetic": True})], ignore_index=True) \
        .to_parquet(root / "rel_order_encumbrance.parquet", index=False)
    rel_instrument = pd.read_parquet(root / "rel_instrument_encumbrance.parquet")
    pd.concat([rel_instrument, pd.DataFrame({"instrument_id": instrument_ids, "encumbrance_id": new_ids, "is_synthetic": True})], ignore_index=True) \
        .to_parquet(root / "rel_instrument_encumbrance.parquet", index=False)

    snapshot = pd.read_parquet(root / "order_risk_snapshot.parquet")
    mask = snapshot["order_id"].isin(order_ids)
    before = snapshot.loc[mask, ["order_id", "risk_score", "risk_band", "blocking_issue_count"]].to_dict(orient="records")
    snapshot.loc[mask, "unresolved_required_clearance_lien"] = True
    snapshot.loc[mask, "blocking_issue_count"] += 1
    snapshot = score_orders(snapshot.drop(columns=["risk_score", "risk_band", "is_at_risk"]))
    snapshot.to_parquet(root / "order_risk_snapshot.parquet", index=False)
    orders = pd.read_parquet(root / "title_order.parquet")
    scores = snapshot.set_index("order_id")
    for column in ["risk_score", "risk_band", "blocking_issue_count", "is_at_risk"]:
        orders.loc[orders["order_id"].isin(order_ids), column] = orders.loc[orders["order_id"].isin(order_ids), "order_id"].map(scores[column])
    orders.to_parquet(root / "title_order.parquet", index=False)
    after = snapshot.loc[mask, ["order_id", "risk_score", "risk_band", "blocking_issue_count"]].to_dict(orient="records")
    report = {"change": "add five fictional open tax liens requiring clearance", "new_encumbrance_ids": new_ids, "before": before, "after": after}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/incremental-change.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

