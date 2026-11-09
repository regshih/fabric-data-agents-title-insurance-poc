from scripts.benchmark_agent import summarize_rows


def test_summary_includes_failed_call_latency() -> None:
    rows = [
        {"success": "True", "total_seconds": "10.0"},
        {"success": "False", "total_seconds": "100.0"},
    ]

    result = summarize_rows(rows, "semantic", "fresh", "sample")

    assert result["success_rate"] == 0.5
    assert result["mean"] == 10.0
    assert result["all_call_latency"]["mean"] == 55.0
    assert result["all_call_latency"]["maximum"] == 100.0
    assert result["failed_call_seconds"] == [100.0]
