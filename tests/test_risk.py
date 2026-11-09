import pandas as pd

from title_iq.risk import score_orders


def test_weighted_risk_is_capped_and_banded() -> None:
    frame = pd.DataFrame({
        "unresolved_required_clearance_lien": [False, True, True],
        "ownership_or_vesting_mismatch": [False, False, True],
        "instrument_after_search_effective_date": [False, True, True],
        "closing_within_three_days_without_commitment": [False, False, True],
        "past_service_level_target": [False, False, True],
        "repeated_search_failure": [False, False, True],
    })
    result = score_orders(frame)
    assert result["risk_score"].tolist() == [0, 50, 100]
    assert result["risk_band"].tolist() == ["Low", "High", "Critical"]
    assert result["is_at_risk"].tolist() == [False, True, True]

