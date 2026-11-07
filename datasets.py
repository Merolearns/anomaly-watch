"""Load the bundled sample datasets (CSV files with timestamp,value)."""

import csv
import os

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")

SAMPLE_DATASETS = {
    "website-traffic": "Website traffic (daily visits)",
    "server-latency": "Server latency (ms, hourly)",
    "daily-sales": "Daily sales (USD)",
}


def load_sample(name):
    """Return (timestamps, values) for a bundled sample dataset."""
    path = os.path.join(SAMPLES_DIR, name + ".csv")
    timestamps, values = [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            timestamps.append(row["timestamp"])
            values.append(float(row["value"]))
    return timestamps, values


def parse_pasted_csv(text):
    """Parse user-pasted CSV text. Accepts timestamp,value rows, with or
    without a header row. Returns (timestamps, values).

    Only the first row is treated as a possible header: a non-numeric
    value anywhere else is a typo in the data, and failing loudly beats
    silently dropping the row and analyzing fewer points than the user
    pasted.
    """
    timestamps, values = [], []
    seen_row = False
    for lineno, line in enumerate(text.strip().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2:
            raise ValueError("each row must have exactly two columns: timestamp,value")
        try:
            value = float(parts[1])
        except ValueError:
            if not seen_row:
                # First row is a header: skip it.
                seen_row = True
                continue
            raise ValueError(f"line {lineno}: value is not a number: {parts[1]!r}")
        seen_row = True
        timestamps.append(parts[0])
        values.append(value)
    if len(values) < 2:
        raise ValueError("need at least 2 data rows")
    return timestamps, values
