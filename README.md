# Anomaly Watch

A time-series anomaly detection dashboard. Pick a sample dataset (or paste
your own CSV), tune the rolling window and z-score threshold, and see
anomalies plotted on a chart with a drill-down table. No JavaScript chart
libraries, no database — the chart is rendered server-side as SVG.

## How it works

For each point, the baseline is the mean and standard deviation of the
*previous* `window` points only. A point is flagged when it sits at least
`threshold` standard deviations from that baseline:

```
z = (value - mean of previous window points) / std of previous window points
```

Using previous points only matters: there is no lookahead. The detector
never peeks at the future, so it behaves the same on live data as on
history. Edge cases: a flat baseline (std = 0) flags only a value that
differs from the baseline, and points with fewer than two predecessors
are never flagged, since one point cannot establish a baseline.

Severity is relative to the threshold: `high` at threshold + 2 or above,
`medium` at threshold + 1 or above, otherwise `low`.

## How to run

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in a browser.

## Example output

Running the detector on the bundled `website-traffic` dataset (120 daily
points, window 20, threshold 3.0) finds **4 anomalies**, with a largest
deviation of 2005.9. Three of them are the injected anomalies in the
sample data; the fourth is a borderline seasonal dip the detector also
flags:

| Timestamp | Value | Rolling mean | Z-score | Direction |
|-----------|-------|--------------|---------|-----------|
| 2026-07-01 | 3200 | 1194.10 | 11.87 | spike |
| 2026-08-15 | 320 | 1225.35 | -4.53 | dip |
| 2026-09-14 | 2900 | 1221.70 | 8.71 | spike |

The dashboard also exposes a JSON API:

```bash
curl -X POST http://127.0.0.1:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"values": [100, 101, 99, 100, 102, 100, 101, 99, 100, 101, 500], "window": 5, "threshold": 3.0}'
```

It returns per-point flags (mean, std, z-score, direction, severity) plus
a summary of points and anomalies found.

## Limitations

- Univariate only: one value series at a time, no correlated signals.
- Needs enough history before it can flag anything — the first points
  are never flagged.
- Threshold tuning is manual; a threshold that is too low flags normal
  noise, and one that is too high misses real breaks.
- Not a forecasting model: it detects deviations from recent history,
  it does not predict future values.
