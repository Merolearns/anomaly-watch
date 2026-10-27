"""Anomaly Watch: a time-series anomaly detection dashboard.

Pick a sample dataset or paste your own CSV, tune the rolling window and
z-score threshold, and see anomalies plotted on a chart. Everything runs
in memory; nothing is stored.
"""

from flask import Flask, jsonify, render_template, request

from datasets import SAMPLE_DATASETS, load_sample, parse_pasted_csv
from detector import detect, summarize

app = Flask(__name__)

DEFAULT_DATASET = "website-traffic"
DEFAULT_WINDOW = 20
DEFAULT_THRESHOLD = 3.0


def build_chart(timestamps, results, width=900, height=320):
    """Render an SVG line chart: values, rolling-mean line, anomaly dots."""
    pad_left, pad_right, pad_top, pad_bottom = 60, 20, 20, 30
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    values = [r["value"] for r in results]
    lo = min(values)
    hi = max(values)
    span = hi - lo or 1.0
    lo -= span * 0.05
    hi += span * 0.05
    span = hi - lo

    def x(i):
        if len(results) <= 1:
            return pad_left
        return pad_left + plot_w * i / (len(results) - 1)

    def y(v):
        return pad_top + plot_h * (1 - (v - lo) / span)

    value_points = " ".join(f"{x(r['index']):.1f},{y(r['value']):.1f}" for r in results)
    mean_points = " ".join(
        f"{x(r['index']):.1f},{y(r['mean']):.1f}"
        for r in results if r["mean"] is not None
    )
    dots = "".join(
        f'<circle cx="{x(r["index"]):.1f}" cy="{y(r["value"]):.1f}" r="5" '
        f'class="anomaly-dot"><title>{timestamps[r["index"]]}: {r["value"]}</title></circle>'
        for r in results if r["is_anomaly"]
    )
    # A few y-axis gridlines with labels.
    grid = ""
    for frac in (0, 0.5, 1.0):
        gy = pad_top + plot_h * frac
        label = hi - span * frac
        grid += (
            f'<line x1="{pad_left}" x2="{width - pad_right}" y1="{gy:.1f}" y2="{gy:.1f}" '
            f'class="gridline"/>'
            f'<text x="{pad_left - 8}" y="{gy + 4:.1f}" class="axis-label" '
            f'text-anchor="end">{label:,.0f}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" '
        f'aria-label="Time series chart with anomalies highlighted">'
        f"{grid}"
        f'<polyline points="{mean_points}" class="mean-line"/>'
        f'<polyline points="{value_points}" class="value-line"/>'
        f"{dots}</svg>"
    )


def analyze(timestamps, values, window, threshold):
    results = detect(values, window, threshold)
    stats = summarize(results)
    anomalies = []
    for r in results:
        if r["is_anomaly"]:
            anomalies.append({
                "timestamp": timestamps[r["index"]],
                "value": r["value"],
                "mean": round(r["mean"], 2),
                "deviation": round(r["value"] - r["mean"], 2),
                "z": round(r["z"], 2) if r["z"] is not None else None,
                "direction": r["direction"],
                "severity": r["severity"],
            })
    return results, stats, anomalies


@app.route("/", methods=["GET", "POST"])
def dashboard():
    dataset = DEFAULT_DATASET
    window = DEFAULT_WINDOW
    threshold = DEFAULT_THRESHOLD
    pasted = ""
    error = None
    source_label = SAMPLE_DATASETS[DEFAULT_DATASET]

    if request.method == "POST":
        try:
            window = int(request.form.get("window", DEFAULT_WINDOW))
            threshold = float(request.form.get("threshold", DEFAULT_THRESHOLD))
            if window < 2:
                raise ValueError("window must be at least 2")
            if threshold <= 0:
                raise ValueError("threshold must be positive")
        except ValueError as exc:
            error = f"Invalid control value: {exc}"
            window, threshold = DEFAULT_WINDOW, DEFAULT_THRESHOLD

        pasted = request.form.get("pasted_csv", "").strip()
        dataset = request.form.get("dataset", DEFAULT_DATASET)
        try:
            if pasted:
                timestamps, values = parse_pasted_csv(pasted)
                source_label = "Pasted CSV"
            else:
                timestamps, values = load_sample(dataset)
                source_label = SAMPLE_DATASETS.get(dataset, dataset)
        except (ValueError, FileNotFoundError, KeyError) as exc:
            error = f"Could not load data: {exc}"
            timestamps, values = load_sample(DEFAULT_DATASET)
            dataset = DEFAULT_DATASET
            source_label = SAMPLE_DATASETS[DEFAULT_DATASET]
    else:
        timestamps, values = load_sample(DEFAULT_DATASET)

    results, stats, anomalies = analyze(timestamps, values, window, threshold)
    chart = build_chart(timestamps, results)
    rows = [
        {"timestamp": timestamps[r["index"]], "value": r["value"],
         "mean": round(r["mean"], 2) if r["mean"] is not None else None,
         "z": round(r["z"], 2) if r["z"] is not None else None,
         "is_anomaly": r["is_anomaly"],
         "direction": r["direction"], "severity": r["severity"]}
        for r in results
    ]
    return render_template(
        "index.html",
        datasets=SAMPLE_DATASETS,
        dataset=dataset,
        window=window,
        threshold=threshold,
        pasted_csv=pasted,
        source_label=source_label,
        stats=stats,
        anomalies=anomalies,
        rows=rows,
        chart=chart,
        error=error,
    )


@app.route("/api/analyze", methods=["GET", "POST"])
def api_analyze():
    if request.method == "GET":
        return jsonify({
            "usage": "POST JSON {\"values\": [...], \"window\": 20, \"threshold\": 3.0}",
            "returns": "per-point flags with mean, std, z, direction and severity",
        })
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "values" not in data:
        return jsonify({"error": "JSON body must contain a 'values' list"}), 400
    try:
        values = [float(v) for v in data["values"]]
        window = int(data.get("window", DEFAULT_WINDOW))
        threshold = float(data.get("threshold", DEFAULT_THRESHOLD))
        results = detect(values, window, threshold)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"invalid input: {exc}"}), 400
    return jsonify({
        "points": results,
        "summary": summarize(results),
    })


if __name__ == "__main__":
    app.run(debug=True)
