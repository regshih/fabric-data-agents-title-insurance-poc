from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def main() -> None:
    root = Path("local-output/data")
    order = pd.read_parquet(root / "title_order.parquet")
    enc = pd.read_parquet(root / "encumbrance.parquet")
    commitment = pd.read_parquet(root / "commitment.parquet")
    policy = pd.read_parquet(root / "policy.parquet")
    summary = {
        "as_of_date": "2026-09-01",
        "data_is_synthetic": True,
        "row_counts": {p.stem: len(pd.read_parquet(p)) for p in sorted(root.glob("*.parquet"))},
        "risk_band_counts": order.groupby("risk_band", observed=True).size().to_dict(),
        "open_orders": int(order["order_status"].isin(["Open", "Search", "CommitmentIssued"]).sum()),
        "at_risk_orders": int(order["is_at_risk"].sum()),
        "unresolved_required_clearance": int(((enc["encumbrance_status"] == "Open") & enc["requires_clearance"]).sum()),
        "issued_commitments": int((commitment["commitment_status"] == "Issued").sum()),
        "issued_policies": int((policy["policy_status"] == "Issued").sum()),
        "top_open_risk_orders": order[order["order_status"].isin(["Open", "Search", "CommitmentIssued"])]
            .sort_values(["risk_score", "days_open"], ascending=False).head(10)[["order_id", "risk_score", "risk_band", "blocking_issue_count"]]
            .to_dict(orient="records"),
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/ground-truth-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

