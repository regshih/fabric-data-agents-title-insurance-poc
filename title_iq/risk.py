from __future__ import annotations

import pandas as pd

RISK_WEIGHTS = {
    "unresolved_required_clearance_lien": 30,
    "ownership_or_vesting_mismatch": 20,
    "instrument_after_search_effective_date": 20,
    "closing_within_three_days_without_commitment": 15,
    "past_service_level_target": 10,
    "repeated_search_failure": 5,
}


def score_orders(features: pd.DataFrame) -> pd.DataFrame:
    required = set(RISK_WEIGHTS)
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"missing risk features: {sorted(missing)}")
    result = features.copy()
    score = sum(result[name].astype(int) * weight for name, weight in RISK_WEIGHTS.items())
    result["risk_score"] = score.clip(upper=100).astype(int)
    result["risk_band"] = pd.cut(
        result["risk_score"],
        bins=[-1, 19, 49, 74, 100],
        labels=["Low", "Medium", "High", "Critical"],
    ).astype(str)
    result["is_at_risk"] = result["risk_score"] >= 50
    return result

