import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from detector import detect


def test_flat_series_yields_no_anomalies():
    results = detect([10, 10, 10, 10, 10, 10], window=3, threshold=3.0)
    assert not any(r["is_anomaly"] for r in results)


def test_clear_spike_is_flagged():
    values = [100, 101, 99, 100, 102, 100, 101, 99, 100, 101, 500]
    results = detect(values, window=5, threshold=3.0)
    assert results[-1]["is_anomaly"]
    assert results[-1]["direction"] == "spike"


def test_clear_dip_is_flagged():
    values = [100, 101, 99, 100, 102, 100, 101, 99, 100, 101, 10]
    results = detect(values, window=5, threshold=3.0)
    assert results[-1]["is_anomaly"]
    assert results[-1]["direction"] == "dip"


def test_std_zero_flags_only_different_value():
    # Flat baseline, then a different value: flagged.
    results = detect([5, 5, 5, 5, 9], window=4, threshold=3.0)
    assert results[-1]["is_anomaly"]
    assert results[-1]["z"] is None
    # Flat baseline continuing: not flagged.
    results = detect([5, 5, 5, 5, 5], window=4, threshold=3.0)
    assert not any(r["is_anomaly"] for r in results)


def test_window_larger_than_series_handled_gracefully():
    # Window bigger than the series: uses whatever history exists, no crash.
    results = detect([10, 11, 10, 11], window=50, threshold=3.0)
    assert len(results) == 4
    assert not any(r["is_anomaly"] for r in results)


def test_first_points_have_no_baseline():
    results = detect([10, 20, 30, 40], window=5, threshold=3.0)
    assert results[0]["mean"] is None
    assert results[1]["mean"] is None
    assert not results[0]["is_anomaly"]
    assert not results[1]["is_anomaly"]


def test_no_lookahead():
    # The spike at the end must not affect earlier flags.
    before = detect([100, 101, 99, 100, 102, 100], window=5, threshold=3.0)
    after = detect([100, 101, 99, 100, 102, 100, 500], window=5, threshold=3.0)
    assert [r["is_anomaly"] for r in before] == [r["is_anomaly"] for r in after[:6]]
