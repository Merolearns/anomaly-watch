"""Rolling-window z-score anomaly detection.

For each point, the baseline is built from the *previous* `window` points
only, never from the point itself and never from future points. That keeps
the detector honest: at any moment it only knows what came before, the way
a live monitor would.
"""

import math


def _mean(values):
    return sum(values) / len(values)


def _std(values, mean):
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def severity_for(z, threshold):
    """Simple severity bands, relative to the chosen threshold."""
    if z is None:
        # Zero-variance baseline broken by a different value: a clear break.
        return "high"
    magnitude = abs(z)
    if magnitude >= threshold + 2:
        return "high"
    if magnitude >= threshold + 1:
        return "medium"
    return "low"


def detect(values, window=20, threshold=3.0):
    """Flag anomalies in a sequence of numbers.

    Args:
        values: list of numbers, in time order.
        window: how many previous points form the baseline.
        threshold: minimum z-score (in standard deviations) to flag.

    Returns a list of dicts, one per point, with keys:
    index, value, mean, std, z, is_anomaly, direction, severity.
    Points with no history yet (fewer than `window` predecessors, or an
    empty baseline) get mean/std/z of None and are never flagged.
    """
    if window < 1:
        raise ValueError("window must be at least 1")
    if threshold <= 0:
        raise ValueError("threshold must be positive")

    results = []
    for i, value in enumerate(values):
        history = values[max(0, i - window):i]
        if len(history) < 2:
            # One predecessor cannot establish a baseline: a single value
            # has no spread, so flagging against it would mark almost
            # every early point. Wait for at least two points of history.
            results.append({
                "index": i, "value": value, "mean": None, "std": None,
                "z": None, "is_anomaly": False, "direction": None,
                "severity": None,
            })
            continue

        mean = _mean(history)
        std = _std(history, mean)

        if std == 0:
            # A flat baseline: any different value is a break, but an
            # equal value is not. There is no meaningful z-score here.
            is_anomaly = value != mean
            z = None
        else:
            z = (value - mean) / std
            is_anomaly = abs(z) >= threshold

        if is_anomaly:
            if value > mean:
                direction = "spike"
            elif value < mean:
                direction = "dip"
            else:
                direction = None
            severity = severity_for(z, threshold)
        else:
            direction = None
            severity = None

        results.append({
            "index": i, "value": value, "mean": mean, "std": std,
            "z": z, "is_anomaly": is_anomaly, "direction": direction,
            "severity": severity,
        })
    return results


def summarize(results):
    """Aggregate stats for a detection run."""
    anomalies = [r for r in results if r["is_anomaly"]]
    largest = None
    if anomalies:
        largest = max(anomalies, key=lambda r: abs(r["value"] - r["mean"]))
    return {
        "points": len(results),
        "anomalies": len(anomalies),
        "largest_deviation": (
            abs(largest["value"] - largest["mean"]) if largest else 0.0
        ),
    }
